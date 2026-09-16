from sqlalchemy import select
from app import main
from app.models import Job
from test_workflow import detect, claim, submit, VECTOR


def test_crop_approval_queues_recognition_and_skips_ignored_heads(api, monkeypatch):
    client, factory, _ = api
    monkeypatch.setattr(main.s, 'auto_recognize', True)
    assert client.get('/api/status').json()['auto_recognize'] is True
    photo, heads, detection = detect(client, boxes=[[1,2,40,50,.9],[45,3,80,60,.8]])
    assert all(h['recognition_state'] == 'queued' for h in heads)
    assert client.post(f"/api/photos/{photo['id']}/recognize").json() == {'queued':0}
    assert submit(client, detection, head_detections=[
        {'body_index':0,'width':100,'height':80,'boxes':[]}]).json()['duplicate']
    with factory() as db:
        assert len(db.scalars(select(Job).where(Job.stage == 'recognition')).all()) == 2
    client.post(f"/api/heads/{heads[0]['id']}/review", json={'state':'ignored'})
    job = claim(client, 'recognition')
    assert job['heads'] == []
    assert submit(client, job, heads=[]).status_code == 200
    job = claim(client, 'recognition')
    assert [h['observation_id'] for h in job['heads']] == [heads[1]['id']]
    assert submit(client, job, heads=[{'observation_id':heads[1]['id'],'embedding':VECTOR}]).status_code == 200


def test_no_heads_does_not_queue_recognition(api, monkeypatch):
    client, _, _ = api
    monkeypatch.setattr(main.s, 'auto_recognize', True)
    detect(client, boxes=[])
    assert claim(client, 'recognition') is None


def test_bear_thumbnail_follows_confirmed_head(api):
    client, _, _ = api
    _, heads, _ = detect(client)
    bear = client.post('/api/bears', json={'name':'Photo Bear'}).json()
    assert client.get('/api/bears').json()[0]['thumbnail_url'] is None
    client.post(f"/api/heads/{heads[0]['id']}/review", json={'state':'confirmed','bear_id':bear['id']})
    assert client.get('/api/bears').json()[0]['thumbnail_url'] == f"/api/heads/{heads[0]['id']}/image?variant=thumbnail-v1"
    client.post(f"/api/heads/{heads[0]['id']}/review", json={'state':'unresolved'})
    assert client.get('/api/bears').json()[0]['thumbnail_url'] is None
