import io
import pytest
from PIL import Image
from fastapi import HTTPException
from sqlalchemy import select
from app import auth, main
from app.models import Organization, Membership, LoginSession, Gallery

def login(api, monkeypatch):
    client, factory, objects = api
    with factory.begin() as db:
        db.add_all([Organization(id='internal-testing',name='Internal Testing'),Organization(id='mcneil',name='McNeil')])
        db.flush()
        db.add_all([Membership(org_id=org,email='tester@gmail.com') for org in ('internal-testing','mcneil')])
        db.add(Gallery(id=2,org_id='mcneil',revision=0))
    with factory() as db:
        raw = auth.admit(db,{'sub':'google-test-user','email':'tester@gmail.com','email_verified':True})
        csrf = db.get(LoginSession,auth.digest(raw)).csrf
    monkeypatch.setattr(main.s,'auth_mode','google')
    client.cookies.set(auth.COOKIE,raw)
    client.headers.update({'origin':main.s.public_origin,'x-csrf-token':csrf,'x-organization-id':'internal-testing'})
    return client, factory, objects

def upload(client):
    f=io.BytesIO(); Image.new('RGB',(30,30),'brown').save(f,'PNG')
    return client.post('/api/photos',files={'files':('same.png',f.getvalue(),'image/png')}).json()['photos'][0]

def test_orgs_isolate_photos_ids_images_and_duplicates(api, monkeypatch):
    client, factory, objects = login(api,monkeypatch)
    first=upload(client)
    assert client.post('/api/session/organization',json={'org_id':'mcneil'}).status_code == 200
    assert client.get('/api/photos').status_code == 409
    client.headers['x-organization-id']='mcneil'
    assert client.get('/api/photos').json() == []
    assert client.get('/api/photos/'+first['id']).status_code == 404
    assert client.get('/api/photos/'+first['id']+'/image').status_code == 404
    second=upload(client)
    assert second['id'] != first['id'] and not second.get('duplicate')
    assert client.post('/api/photos/'+first['id']+'/recognize').status_code == 404
    assert any('photos/mcneil/' in key for key in objects)
    assert client.post('/api/session/organization',json={'org_id':'other'}).status_code == 403

def test_logout_csrf_and_membership_revocation(api, monkeypatch):
    client, factory, _ = login(api,monkeypatch)
    first=upload(client)
    assert client.get('/api/photos').headers['cache-control'] == 'private, no-store'
    csrf=client.headers.pop('x-csrf-token')
    assert client.post('/api/session/logout').status_code == 403
    client.headers['x-csrf-token']=csrf
    raw=client.cookies.get(auth.COOKIE)
    assert client.post('/api/session/logout').status_code == 200
    assert client.get('/api/photos').status_code == 401
    client.cookies.set(auth.COOKIE,raw)
    assert client.get('/api/photos/'+first['id']+'/image').status_code == 401

def test_uninvited_google_identity_is_denied(api):
    _, factory, _=api
    with factory() as db:
        with pytest.raises(HTTPException) as error:
            auth.admit(db,{'sub':'stranger','email':'stranger@gmail.com','email_verified':True})
        assert error.value.status_code == 403

def test_worker_matching_and_bear_assignment_stay_in_org(api, monkeypatch):
    from test_workflow import detect, recognize
    client, factory, _ = login(api,monkeypatch)
    photo, heads, _ = detect(client)
    recognize(client, photo, heads)
    bear=client.post('/api/bears',json={'name':'Internal only'}).json()
    client.post('/api/heads/'+heads[0]['id']+'/review',json={'state':'confirmed','bear_id':bear['id']})
    client.post('/api/session/organization',json={'org_id':'mcneil'})
    client.headers['x-organization-id']='mcneil'
    other, other_heads, _ = detect(client)
    assert client.get('/api/bears').json() == []
    assert client.get('/api/heads/'+heads[0]['id']+'/history').status_code == 404
    assert client.post('/api/heads/'+other_heads[0]['id']+'/review',json={'state':'confirmed','bear_id':bear['id']}).status_code == 404
    recognize(client, other, other_heads)
    detail=client.get('/api/photos/'+other['id']).json()
    assert detail['heads'][0]['suggestions'][0]['candidates'] == []

def test_revoked_or_expired_session_cannot_access_org(api, monkeypatch):
    from datetime import timedelta
    from app.models import now
    client, factory, _=login(api,monkeypatch)
    with factory.begin() as db:
        session=db.scalar(select(LoginSession))
        session.expires_at=now()-timedelta(seconds=1)
    assert client.get('/api/photos').status_code == 401
    with factory.begin() as db:
        session=db.scalar(select(LoginSession))
        session.expires_at=now()+timedelta(days=1)
        db.delete(db.get(Membership,('internal-testing','tester@gmail.com')))
    assert client.get('/api/photos').status_code == 403
    assert client.get('/auth/me').json()['org_id'] == 'mcneil'
    assert client.get('/api/photos').status_code == 409
    client.headers['x-organization-id']='mcneil'
    assert client.get('/api/photos').status_code == 200

def test_google_callback_rejects_unknown_state_without_session(api, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(main.s,'auth_mode','google')
    monkeypatch.setattr(main.s,'google_client_id','test-client')
    monkeypatch.setattr(main.s,'google_client_secret','test-secret')
    monkeypatch.setattr(main.s,'oauth_cookie_secret','test-cookie-key-at-least-32-characters-long')
    app=FastAPI()
    auth.install(app)
    with TestClient(app,base_url='https://testserver') as client:
        response=client.get('/auth/callback?code=untrusted&state=unknown',follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == '/?login=denied'
        assert auth.COOKIE not in client.cookies
