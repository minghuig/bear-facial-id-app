import os
import subprocess
import sys
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
    env={**os.environ,'DATABASE_URL':url,'PGOPTIONS':f'-csearch_path={schema}',
         'PIPELINE':'real-v1-upgraded'}
    cwd=Path(__file__).resolve().parents[1]/'backend'
    try:
        subprocess.run([sys.executable,'-m','alembic','upgrade','0001'],cwd=cwd,env=env,check=True,capture_output=True)
        with engine.begin() as db:
            db.execute(text(f"INSERT INTO {schema}.bears(id,created_at,name) VALUES ('old',now(),'Existing Bear')"))
            db.execute(text(f"INSERT INTO {schema}.batches(id,created_at) VALUES ('old-batch',now())"))
            for photo_id, sha, pipeline in [('real-photo','real-sha','real-v1-legacy'),
                                            ('mock-photo','mock-sha','mock-v1'),
                                            ('pending-photo','pending-sha','real-v1-legacy')]:
                db.execute(text(f"""INSERT INTO {schema}.photos
                    (id,created_at,batch_id,sha256,filename,original_key,oriented_key,
                     width,height,detection_state,pipeline,detections,provenance)
                    VALUES (:id,now(),'old-batch',:sha,'old.jpg','original','oriented',
                            100,80,:state,:pipeline,'[]','{{}}')"""),
                    {'id':photo_id,'sha':sha,'pipeline':pipeline,
                     'state':'queued' if photo_id == 'pending-photo' else 'complete'})
                if photo_id == 'pending-photo':
                    continue
                db.execute(text(f"""INSERT INTO {schema}.observations
                    (id,created_at,photo_id,index,box,crop_key,pipeline,
                     recognition_state,review_state,embedding,diagnostics)
                    VALUES (:id,now(),:photo_id,0,'[0,0,10,10]','crop',:pipeline,
                            'not_requested','unresolved',NULL,'{{}}')"""),
                    {'id':photo_id+'-head','photo_id':photo_id,'pipeline':pipeline})
            db.execute(text(f"""INSERT INTO {schema}.jobs
                (id,created_at,photo_id,stage,pipeline,observation_ids,state,attempts)
                VALUES ('old-detection',now(),'pending-photo','detection',
                        'real-v1-legacy','[]','queued',0)"""))
            db.execute(text(f"""INSERT INTO {schema}.jobs
                (id,created_at,photo_id,stage,pipeline,observation_ids,state,attempts,token)
                VALUES ('old-recognition',now(),'real-photo','recognition',
                        'real-v1-legacy','[\"real-photo-head\"]','running',1,'old-token')"""))
            db.execute(text(f"""INSERT INTO {schema}.attempts
                (id,created_at,job_id,token,state)
                VALUES ('old-attempt',now(),'old-recognition','old-token','running')"""))
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=cwd,env=env,check=True,capture_output=True)
        with engine.connect() as db:
            assert db.execute(text(f'SELECT org_id FROM {schema}.bears')).scalar_one() == 'internal-testing'
            assert db.execute(text(f'SELECT count(*) FROM {schema}.organizations')).scalar_one() == 2
            assert db.execute(text(f"SELECT count(*) FROM {schema}.photos WHERE org_id='mcneil'")).scalar_one() == 0
            rows = db.execute(text(f"SELECT id,embedding_space,crop_review_state FROM {schema}.observations")).all()
            assert sorted(rows) == sorted([
                ('real-photo-head','poseswin-test-on-2020-v1','accepted'),
                ('mock-photo-head','mock-v1','accepted'),
            ])
            assert db.execute(text(f"SELECT body_detections FROM {schema}.photos LIMIT 1")).scalar_one() == []
            jobs = db.execute(text(f"SELECT stage,state,pipeline FROM {schema}.jobs")).all()
            assert sorted(jobs) == sorted([
                ('detection','superseded','real-v1-legacy'),
                ('recognition','superseded','real-v1-legacy'),
                ('body_detection','queued','real-v1-upgraded'),
                ('recognition','queued','real-v1-upgraded'),
            ])
            assert db.execute(text(f"SELECT pipeline FROM {schema}.photos WHERE id='pending-photo'")).scalar_one() == 'real-v1-upgraded'
            assert db.execute(text(f"SELECT pipeline FROM {schema}.photos WHERE id='real-photo'")).scalar_one() == 'real-v1-legacy'
            assert db.execute(text(f"SELECT state FROM {schema}.attempts WHERE id='old-attempt'")).scalar_one() == 'failed'
            recognized = db.execute(text(f"""SELECT observation_ids FROM {schema}.jobs
                WHERE stage='recognition' AND state='queued'""")).scalar_one()
            assert recognized == ['real-photo-head']
    finally:
        with engine.begin() as db:
            db.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        engine.dispose()
