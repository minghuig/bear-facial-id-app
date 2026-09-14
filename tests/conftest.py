"""API integration tests use an isolated PostgreSQL schema and in-memory S3 adapter."""
import os
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
os.environ.setdefault('WORKER_TOKEN', 'test-worker-token-at-least-24-characters')
os.environ.setdefault('DATABASE_URL', os.getenv('TEST_DATABASE_URL', 'postgresql+psycopg://localhost/postgres'))

@pytest.fixture
def api(monkeypatch):
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set TEST_DATABASE_URL to a disposable PostgreSQL database; SQLite cannot validate queue locks')
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from fastapi.testclient import TestClient
    from app import main, storage
    # Most workflow tests exercise the supported manual mode. Automatic mode
    # has focused coverage in test_auto_recognition.py.
    monkeypatch.setattr(main.s, 'auto_recognize', False)
    from app.db import session
    from app.models import Base, Gallery
    schema = 'test_' + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA {schema}'))
    engine = create_engine(url, connect_args={'options': f'-csearch_path={schema}'})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add(Gallery(id=1, revision=0))
    from fastapi import Request
    from app import auth
    monkeypatch.setattr(auth, 'Session', factory)
    def override(request: Request):
        with factory() as db:
            if request.url.path.startswith('/api/'):
                db.info['org_id'] = request.state.org_id
            yield db
    main.app.dependency_overrides[session] = override
    objects = {}
    monkeypatch.setattr(storage, 'put', lambda key, data, content_type='image/png': objects.__setitem__(key, data))
    monkeypatch.setattr(storage, 'get', lambda key: objects[key])
    monkeypatch.setattr(storage, 'get_optional', lambda key: objects.get(key))
    monkeypatch.setattr(storage, 'signed', lambda key: 'https://storage.invalid/' + key)
    monkeypatch.setattr(storage, 'delete_many', lambda keys: [objects.pop(key, None) for key in keys])
    try:
        with TestClient(main.app) as client:
            yield client, factory, objects
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()
