from sqlalchemy import select
from app import main
from app.models import Observation, Photo, Job
from test_workflow import detect, claim, submit, VECTOR


def test_recognition_retry_uses_current_model_without_relabeling_old_embeddings(api):
    client, factory, _ = api
    photo, heads, _ = detect(client, boxes=[[1,2,40,50,.9], [45,3,80,60,.8]])
    with factory.begin() as db:
        db.get(Photo, photo['id']).pipeline = 'retired-pipeline'
        failed = db.get(Observation, heads[0]['id'])
        failed.pipeline = 'retired-pipeline'
        failed.recognition_state = 'failed'
        done = db.get(Observation, heads[1]['id'])
        done.pipeline = 'retired-pipeline'
        done.recognition_state = 'complete'
        done.embedding = VECTOR
    assert client.post(f"/api/photos/{photo['id']}/recognize").json() == {'queued': 1}
    job = claim(client, 'recognition')
    assert job is not None
    assert submit(client, job, heads=[{'observation_id': heads[0]['id'], 'embedding': VECTOR}]).status_code == 200
    with factory() as db:
        assert db.get(Observation, heads[0]['id']).pipeline == main.s.pipeline
        assert db.get(Observation, heads[1]['id']).pipeline == 'retired-pipeline'
        assert db.get(Photo, photo['id']).pipeline == 'retired-pipeline'
