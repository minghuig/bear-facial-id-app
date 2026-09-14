import os
import subprocess
import uuid
from pathlib import Path
import pytest
from sqlalchemy import create_engine, text

def test_upgrade_preserves_legacy_data_in_testing_and_mcneil_empty():
    url=os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('PostgreSQL required')
    engine=create_engine(url)
    schema='migration_'+uuid.uuid4().hex
    with engine.begin() as db:
        db.execute(text(f'CREATE SCHEMA {schema}'))
    env={**os.environ,'DATABASE_URL':url,'PGOPTIONS':f'-csearch_path={schema}'}
    cwd=Path(__file__).resolve().parents[1]/'backend'
    try:
        subprocess.run(['alembic','upgrade','0001'],cwd=cwd,env=env,check=True,capture_output=True)
        with engine.begin() as db:
            db.execute(text(f"INSERT INTO {schema}.bears(id,created_at,name) VALUES ('old',now(),'Existing Bear')"))
        subprocess.run(['alembic','upgrade','head'],cwd=cwd,env=env,check=True,capture_output=True)
        with engine.connect() as db:
            assert db.execute(text(f'SELECT org_id FROM {schema}.bears')).scalar_one() == 'internal-testing'
            assert db.execute(text(f'SELECT count(*) FROM {schema}.organizations')).scalar_one() == 2
            assert db.execute(text(f"SELECT count(*) FROM {schema}.photos WHERE org_id='mcneil'")).scalar_one() == 0
    finally:
        with engine.begin() as db:
            db.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        engine.dispose()
