"""A single configured Google identity can manage organization invitations."""
import logging
import re
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .auth import current
from .db import session
from .models import LoginSession, Membership, Organization, User

DB = Annotated[Session, Depends(session)]
log = logging.getLogger('uvicorn.error')


class MembershipInput(BaseModel):
    org_id: str = Field(min_length=1, max_length=36)
    email: str = Field(min_length=3, max_length=320)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", email):
            raise ValueError('Enter the exact Google account email address')
        return email


def require_owner(request: Request, db: Session, config) -> User:
    if (config.local_owner_settings and config.auth_mode == 'local'
            and config.environment == 'local' and not config.public_deployment):
        return User(id='local-test-owner', google_sub='local-test-owner', email='Local development')
    owner_sub = config.owner_google_sub
    if config.auth_mode != 'google' or not owner_sub:
        raise HTTPException(403, 'Owner access required')
    login = current(db, request)
    user = db.get(User, login.user_id)
    if not user or user.google_sub != owner_sub:
        raise HTTPException(403, 'Owner access required')
    return user


def member_json(member: Membership, owner_id: str) -> dict:
    return {'org_id':member.org_id, 'email':member.email,
            'status':'active' if member.user_id else 'pending',
            'is_owner':member.user_id == owner_id}


def install(app, config):
    @app.get('/api/admin/memberships')
    def list_memberships(request: Request, db: DB):
        owner = require_owner(request, db, config)
        orgs = db.scalars(select(Organization).order_by(Organization.name)).all()
        members = db.scalars(select(Membership).order_by(Membership.org_id, Membership.email)).all()
        return {'organizations':[{'id':org.id,'name':org.name} for org in orgs],
                'memberships':[member_json(member, owner.id) for member in members]}

    @app.post('/api/admin/memberships')
    def invite_member(body: MembershipInput, request: Request, db: DB):
        owner = require_owner(request, db, config)
        if not db.get(Organization, body.org_id):
            raise HTTPException(404, 'Organization not found')
        member = db.get(Membership, (body.org_id, body.email))
        created = member is None
        if created:
            member = Membership(org_id=body.org_id, email=body.email)
            db.add(member)
            db.commit()
            log.info('Membership invited by owner_user_id=%s org_id=%s email=%s', owner.id, body.org_id, body.email)
        return {**member_json(member, owner.id), 'created':created}

    @app.delete('/api/admin/memberships')
    def remove_member(body: MembershipInput, request: Request, db: DB):
        owner = require_owner(request, db, config)
        member = db.scalar(select(Membership).where(Membership.org_id == body.org_id,
                                                    Membership.email == body.email).with_for_update())
        if member is None:
            raise HTTPException(404, 'Membership not found')
        if member.user_id == owner.id:
            raise HTTPException(409, 'The owner cannot remove their own access')
        if member.user_id:
            db.execute(delete(LoginSession).where(LoginSession.user_id == member.user_id,
                                                  LoginSession.org_id == body.org_id))
        db.delete(member)
        db.commit()
        log.info('Membership removed by owner_user_id=%s org_id=%s email=%s', owner.id, body.org_id, body.email)
        return {'removed':True}
