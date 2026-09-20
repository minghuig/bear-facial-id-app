"""Owner-only invitation management, using a disposable in-memory database."""
import sys
from datetime import datetime, timedelta

from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import auth, main, manage_members
from app.db import session
from app.models import Base, LoginSession, Membership, Organization, User


def test_owner_can_manage_memberships_but_members_cannot(monkeypatch, capsys):
    engine = create_engine('sqlite+pysqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    expiry = datetime.now() + timedelta(days=1)
    monkeypatch.setattr(auth, 'now', datetime.now)
    monkeypatch.setattr(auth, 'Session', factory)
    monkeypatch.setattr(manage_members, 'Session', factory)
    monkeypatch.setattr(main.s, 'auth_mode', 'google')
    monkeypatch.setattr(main.s, 'owner_google_sub', 'owner-google-sub')
    with factory.begin() as db:
        db.add_all([Organization(id='internal-testing', name='Internal Testing'),
                    Organization(id='mcneil', name='McNeil')])
        db.add_all([User(id='owner', google_sub='owner-google-sub', email='owner@gmail.com'),
                    User(id='member', google_sub='member-google-sub', email='member@gmail.com')])
        db.flush()
        db.add_all([Membership(org_id='internal-testing', email='owner@gmail.com', user_id='owner'),
                    Membership(org_id='internal-testing', email='member@gmail.com', user_id='member'),
                    Membership(org_id='mcneil', email='member@gmail.com', user_id='member')])
        db.add_all([LoginSession(token_hash=auth.digest('owner-token'), user_id='owner', org_id='internal-testing', csrf='owner-csrf', expires_at=expiry),
                    LoginSession(token_hash=auth.digest('member-token'), user_id='member', org_id='internal-testing', csrf='member-csrf', expires_at=expiry),
                    LoginSession(token_hash=auth.digest('member-mcneil-token'), user_id='member', org_id='mcneil', csrf='member-csrf', expires_at=expiry)])

    monkeypatch.setattr(sys, 'argv', ['manage_members', 'lookup-sub', 'internal-testing', 'owner@gmail.com'])
    manage_members.main()
    assert capsys.readouterr().out.strip() == 'owner-google-sub'

    def override(request: Request):
        with factory() as db:
            if request.url.path.startswith('/api/'):
                db.info['org_id'] = request.state.org_id
            yield db

    main.app.dependency_overrides[session] = override
    try:
        with TestClient(main.app) as client:
            client.cookies.set(auth.COOKIE, 'member-token')
            client.headers.update({'origin':main.s.public_origin, 'x-csrf-token':'member-csrf',
                                   'x-organization-id':'internal-testing'})
            assert client.get('/auth/me').json()['is_owner'] is False
            assert client.get('/api/admin/memberships').status_code == 403
            body = {'org_id':'mcneil', 'email':'new@gmail.com'}
            assert client.post('/api/admin/memberships', json=body).status_code == 403
            assert client.request('DELETE', '/api/admin/memberships', json=body).status_code == 403

            client.cookies.set(auth.COOKIE, 'owner-token')
            client.headers['x-csrf-token'] = 'owner-csrf'
            assert client.get('/auth/me').json()['is_owner'] is True
            listing_response = client.get('/api/admin/memberships')
            assert listing_response.status_code == 200, listing_response.text
            listed = listing_response.json()
            assert len(listed['organizations']) == 2
            assert any(row['email'] == 'member@gmail.com' and row['org_id'] == 'mcneil' for row in listed['memberships'])
            assert client.post('/api/admin/memberships', json=body, headers={'x-csrf-token':'wrong'}).status_code == 403
            assert client.post('/api/admin/memberships', json={'org_id':'mcneil','email':'bad email'}).status_code == 422
            assert client.post('/api/admin/memberships', json={'org_id':'missing','email':'new@gmail.com'}).status_code == 404
            response = client.post('/api/admin/memberships', json={'org_id':'mcneil','email':' NEW@GMAIL.COM '})
            assert response.status_code == 200
            assert response.json()['email'] == 'new@gmail.com'
            assert response.json()['status'] == 'pending'
            assert response.json()['created'] is True
            assert client.post('/api/admin/memberships', json=body).json()['created'] is False
            assert client.request('DELETE', '/api/admin/memberships', json={'org_id':'internal-testing','email':'owner@gmail.com'}).status_code == 409
            assert client.request('DELETE', '/api/admin/memberships', json={'org_id':'mcneil','email':'member@gmail.com'}).status_code == 200

            with factory() as db:
                assert db.get(Membership, ('mcneil','member@gmail.com')) is None
                assert db.get(Membership, ('internal-testing','member@gmail.com')) is not None
                assert db.get(LoginSession, auth.digest('member-mcneil-token')) is None
                assert db.get(LoginSession, auth.digest('member-token')) is not None
            client.cookies.set(auth.COOKIE, 'member-mcneil-token')
            client.headers['x-organization-id'] = 'mcneil'
            assert client.get('/api/admin/memberships').status_code == 401
            client.cookies.set(auth.COOKIE, 'member-token')
            client.headers['x-organization-id'] = 'internal-testing'
            assert client.get('/auth/me').status_code == 200
            client.cookies.set(auth.COOKIE, 'owner-token')
            client.headers['x-csrf-token'] = 'owner-csrf'
            monkeypatch.setattr(main.s, 'owner_google_sub', '')
            assert client.get('/auth/me').json()['is_owner'] is False
            assert client.get('/api/admin/memberships').status_code == 403
            monkeypatch.setattr(main.s, 'auth_mode', 'local')
            monkeypatch.setattr(main.s, 'environment', 'local')
            monkeypatch.setattr(main.s, 'local_owner_settings', True)
            monkeypatch.setattr(main.s, 'cors_origin', 'http://localhost:5174')
            assert client.get('/auth/me').json()['is_owner'] is True
            assert client.get('/api/admin/memberships').status_code == 200
            assert client.post('/api/admin/memberships', json={'org_id':'mcneil','email':'local@gmail.com'},
                               headers={'origin':'http://127.0.0.1:5174'}).status_code == 200
            monkeypatch.setattr(main.s, 'public_deployment', True)
            assert client.get('/api/admin/memberships').status_code == 403
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
