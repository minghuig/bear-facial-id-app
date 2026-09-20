"""Invite-only Google login and revocable organization-scoped browser sessions."""
import hashlib
import secrets
from datetime import timedelta
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from .config import settings
from .db import Session
from .models import User, Membership, Organization, LoginSession, now, uid

COOKIE = 'bear_session'
def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def admit(db, claims):
    email = str(claims.get('email', '')).lower()
    sub = claims.get('sub')
    if not sub or claims.get('email_verified') is not True:
        raise HTTPException(403, 'Invited Google account required')
    user = db.scalar(select(User).where(User.google_sub == sub))
    # Bind only Google-authoritative addresses automatically. Third-party
    # addresses require an operator to bind a verified sub in advance.
    authoritative = email.endswith('@gmail.com') or bool(claims.get('hd'))
    invites = db.scalars(select(Membership).where(Membership.email == email).with_for_update()).all()
    if user is None:
        if not authoritative or not any(m.user_id is None for m in invites):
            raise HTTPException(403, 'This Google account is not invited')
        user = User(id=uid(), google_sub=sub, email=email)
        db.add(user)
        db.flush()
    if authoritative:
        for member in invites:
            if member.user_id is None:
                member.user_id = user.id
    db.flush()
    memberships = db.scalars(select(Membership).where(Membership.user_id == user.id).order_by(Membership.org_id)).all()
    if not memberships:
        raise HTTPException(403, 'This Google account is not invited')
    raw = secrets.token_urlsafe(32)
    login = LoginSession(token_hash=digest(raw), user_id=user.id, org_id=memberships[0].org_id,
                         csrf=secrets.token_hex(32), expires_at=now()+timedelta(days=7))
    db.add(login)
    db.commit()
    return raw

def current(db, request, require_membership=True):
    raw = request.cookies.get(COOKIE, '')
    login = db.get(LoginSession, digest(raw)) if raw else None
    if not login or login.expires_at <= now():
        raise HTTPException(401, 'Sign in required')
    if require_membership and not db.scalar(select(Membership).where(Membership.user_id == login.user_id, Membership.org_id == login.org_id)):
        raise HTTPException(403, 'Organization access revoked')
    return login

def install(app):
    s = settings()
    oauth = None
    if s.auth_mode == 'google':
        from authlib.integrations.starlette_client import OAuth
        from starlette.middleware.sessions import SessionMiddleware
        oauth = OAuth()
        oauth.register('google', client_id=s.google_client_id, client_secret=s.google_client_secret,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope':'openid email profile', 'code_challenge_method':'S256'})
        app.add_middleware(SessionMiddleware, secret_key=s.oauth_cookie_secret,
                           session_cookie='bear_oauth', max_age=600, https_only=True, same_site='lax')

    @app.middleware('http')
    async def guard(request: Request, call_next):
        protected = request.url.path.startswith('/api/')
        try:
            if protected:
                if s.auth_mode == 'local':
                    request.state.org_id = 'internal-testing'
                else:
                    with Session() as db:
                        login = current(db, request, require_membership=request.url.path != '/api/session/logout')
                        request.state.org_id = login.org_id
                        if not request.url.path.endswith('/image') and request.headers.get('x-organization-id') != login.org_id:
                            raise HTTPException(409, 'Organization changed; reload the page')
                        if request.method not in ('GET','HEAD','OPTIONS'):
                            if request.headers.get('origin') != s.public_origin or not secrets.compare_digest(
                                    request.headers.get('x-csrf-token', ''), login.csrf):
                                raise HTTPException(403, 'Invalid request origin or CSRF token')
            response = await call_next(request)
        except HTTPException as error:
            response = JSONResponse({'detail':error.detail}, status_code=error.status_code)
        if protected or request.url.path.startswith('/auth/'):
            response.headers['Cache-Control'] = 'private, no-store'
        return response

    @app.get('/auth/login')
    async def login(request: Request):
        if oauth is None:
            raise HTTPException(404)
        return await oauth.google.authorize_redirect(request, s.public_origin+'/auth/callback')

    @app.get('/auth/callback')
    async def callback(request: Request):
        if oauth is None:
            raise HTTPException(404)
        try:
            token = await oauth.google.authorize_access_token(request)
            with Session() as db:
                raw = admit(db, token['userinfo'])
        except Exception:
            # Never expose OAuth codes, tokens or provider errors in a response.
            return RedirectResponse('/?login=denied', status_code=303)
        request.session.clear()
        response = RedirectResponse('/', status_code=303)
        response.set_cookie(COOKIE, raw, max_age=604800, secure=True, httponly=True, samesite='lax')
        return response

    @app.get('/auth/me')
    def me(request: Request):
        if s.auth_mode == 'local':
            return {'mode':'local','email':'Local development','org_id':'internal-testing',
                    'organizations':[{'id':'internal-testing','name':'Internal Testing'}],
                    'csrf':'', 'is_owner':s.local_owner_settings}
        with Session() as db:
            login = current(db, request, require_membership=False)
            user = db.get(User, login.user_id)
            orgs = db.execute(select(Organization.id, Organization.name).join(
                Membership, Membership.org_id == Organization.id).where(Membership.user_id == login.user_id)).all()
            if not orgs:
                db.delete(login)
                db.commit()
                raise HTTPException(403, 'Organization access revoked')
            if login.org_id not in [oid for oid,_ in orgs]:
                login.org_id = orgs[0][0]
                db.commit()
            return {'mode':'google','email':user.email,'org_id':login.org_id,'csrf':login.csrf,
                    'is_owner':bool(s.owner_google_sub and user.google_sub == s.owner_google_sub),
                    'organizations':[{'id':oid,'name':name} for oid,name in orgs]}

    @app.post('/api/session/organization')
    async def switch(request: Request):
        if s.auth_mode != 'google':
            raise HTTPException(403)
        body = await request.json()
        with Session() as db:
            login = current(db, request)
            org = body.get('org_id')
            if not db.scalar(select(Membership).where(Membership.user_id == login.user_id, Membership.org_id == org)):
                raise HTTPException(403, 'Not a member of this organization')
            login.org_id = org
            db.commit()
        return {'ok':True}

    @app.post('/api/session/logout')
    def logout(request: Request):
        with Session() as db:
            login = current(db, request, require_membership=False)
            db.delete(login)
            db.commit()
        response = JSONResponse({'ok':True})
        response.delete_cookie(COOKIE, secure=True, httponly=True, samesite='lax')
        return response
