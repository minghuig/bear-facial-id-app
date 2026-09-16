import io
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from PIL import Image
from sqlalchemy import select

from app.models import Attempt, Job, Observation, Photo, Suggestion, now

AUTH = {'Authorization': 'Bearer test-worker-token-at-least-24-characters'}
VECTOR = [1.0] + [0.0] * 511


def upload(client, color='brown'):
    stream = io.BytesIO()
    Image.new('RGB', (100, 80), color).save(stream, 'PNG')
    response = client.post('/api/photos', files={'files': ('bear.png', stream.getvalue(), 'image/png')})
    assert response.status_code == 200, response.text
    return response.json()['photos'][0]


def claim(client, stage='body_detection'):
    response = client.post('/internal/jobs/claim', headers=AUTH, json={'stage': stage, 'pipeline': 'mock-v1'})
    assert response.status_code == 200, response.text
    return response.json()


def submit(client, job, **fields):
    return client.post(f"/internal/jobs/{job['job_id']}/result", headers=AUTH, json={
        'token': job['token'], 'pipeline': 'mock-v1', 'provenance': {'mode': 'mock'}, **fields})


def detect(client, color='brown', boxes=None, approve=True):
    photo = upload(client, color)
    body_job = claim(client)
    head_boxes = boxes if boxes is not None else [[1, 2, 40, 50, .9]]
    response = submit(client, body_job, body_detection={'width': 100, 'height': 80,
        'detections': [] if not head_boxes else [
            {'category': 1, 'confidence': .95, 'bbox': [0, 0, 1, 1]}]})
    assert response.status_code == 200, response.text
    job = body_job
    if head_boxes:
        job = claim(client, 'head_detection')
        assert len(job['bodies']) == 1
        response = submit(client, job, head_detections=[{'body_index': 0,
            'width': 100, 'height': 80, 'boxes': head_boxes}])
        assert response.status_code == 200, response.text
    heads = client.get(f"/api/photos/{photo['id']}").json()['heads']
    if approve:
        for head in heads:
            response = client.post(f"/api/heads/{head['id']}/crop-review", json={'state': 'accepted'})
            assert response.status_code == 200, response.text
        heads = client.get(f"/api/photos/{photo['id']}").json()['heads']
    return photo, heads, job


def recognize(client, photo, heads):
    assert client.post(f"/api/photos/{photo['id']}/recognize").json()['queued'] == len(heads)
    job = claim(client, 'recognition')
    response = submit(client, job, heads=[{'observation_id': h['id'], 'embedding': VECTOR} for h in heads])
    assert response.status_code == 200, response.text
    return job


def test_pause_survives_new_sessions_and_duplicate_result(api):
    client, factory, objects = api
    assert client.get('/api/status').json()['auto_recognize'] is False
    photo, heads, job = detect(client, boxes=[[1, 2, 40, 50, .9], [45, 3, 80, 60, .8]])
    assert len(heads) == 2
    assert claim(client, 'recognition') is None
    with factory() as db:
        assert db.get(Photo, photo['id']).detection_state == 'complete'
        assert {x.recognition_state for x in db.scalars(select(Observation))} == {'not_requested'}
        assert len(db.scalars(select(Job)).all()) == 2
    assert submit(client, job, head_detections=[{'body_index':0, 'width':100, 'height':80,
        'boxes':[]}]).json()['duplicate']
    assert len(client.get(f"/api/photos/{photo['id']}").json()['heads']) == 2
    assert client.post(f"/api/heads/{heads[1]['id']}/review", json={'state': 'ignored'}).status_code == 200
    recognize(client, photo, heads[:1])
    assert client.post(f"/api/photos/{photo['id']}/recognize").json() == {'queued': 0}
    current = client.get(f"/api/photos/{photo['id']}").json()['heads']
    assert current[0]['suggestions'][0]['candidates'] == []
    assert current[1]['recognition_state'] == 'not_requested'


def test_dedup_no_heads_and_invalid_upload(api):
    client, factory, _ = api
    photo, heads, _ = detect(client, boxes=[])
    assert not heads
    assert upload(client)['duplicate'] is True
    assert client.post(f"/api/photos/{photo['id']}/recognize").json() == {'queued': 0}
    response = client.post('/api/photos', files={'files': ('bad.png', b'not image', 'image/png')})
    assert 'error' in response.json()['photos'][0]
    with factory() as db:
        assert len(db.scalars(select(Photo)).all()) == 1
        assert len(db.scalars(select(Job)).all()) == 1


def test_detected_crops_require_explicit_curation(api):
    client, _, _ = api
    photo, heads, _ = detect(client, boxes=[[1,2,40,50,.9], [45,3,80,60,.8]],
                              approve=False)
    assert [head['crop_review_state'] for head in heads] == ['pending', 'pending']
    assert client.get('/api/photos').json()[0]['status_label'] == 'Review detected crops'
    assert client.post(f"/api/photos/{photo['id']}/recognize").json() == {'queued':0}
    assert client.post(f"/api/heads/{heads[0]['id']}/review",
                       json={'state':'unresolved'}).status_code == 409
    accepted = client.post(f"/api/heads/{heads[0]['id']}/crop-review",
                           json={'state':'accepted'})
    rejected = client.post(f"/api/heads/{heads[1]['id']}/crop-review",
                           json={'state':'rejected'})
    assert accepted.status_code == rejected.status_code == 200
    assert client.post(f"/api/photos/{photo['id']}/recognize").json() == {'queued':1}
    assert client.get(f"/api/heads/{heads[0]['id']}/crop-history").json()[0]['state'] == 'accepted'
    assert client.get(f"/api/heads/{heads[1]['id']}/crop-history").json()[0]['state'] == 'rejected'


def test_head_boxes_are_relative_to_padded_body_crops(api):
    client, factory, objects = api
    photo = upload(client)
    body_job = claim(client)
    result = submit(client, body_job, body_detection={'width':100,'height':80,
        'detections':[{'category':1,'confidence':.95,'bbox':[.2,.25,.5,.5]}]})
    assert result.status_code == 200, result.text
    head_job = claim(client, 'head_detection')
    assert [(body['index'],body['crop_box'],body['width'],body['height'])
            for body in head_job['bodies']] == [(0,[17,18,73,62],56,44)]
    result = submit(client, head_job, head_detections=[{'body_index':0,'width':56,
        'height':44,'boxes':[[0,0,20,10,.9], [25,25,30,30,.49]]}])
    assert result.status_code == 200, result.text
    head = client.get(f"/api/photos/{photo['id']}").json()['heads'][0]
    assert head['box'] == [17,18,37,28]
    assert head['body_index'] == 0 and head['crop_review_state'] == 'pending'
    with factory() as db:
        body = db.get(Photo, photo['id']).body_detections[0]
        assert len(db.get(Photo, photo['id']).detections[0]['boxes']) == 2
        assert Image.open(io.BytesIO(objects[body['crop_key']])).size == (56,44)
        observation = db.get(Observation, head['id'])
        assert Image.open(io.BytesIO(objects[observation.crop_key])).size == (20,10)


def test_rejected_crop_does_not_reenter_gallery_after_inflight_worker_error(api):
    client, factory, _ = api
    photo, heads, _ = detect(client)
    path = f"/api/heads/{heads[0]['id']}"
    assert client.post(f"/api/photos/{photo['id']}/recognize").json() == {'queued':1}
    job = claim(client, 'recognition')
    assert client.post(path+'/crop-review',json={'state':'rejected'}).status_code == 200
    assert submit(client,job,error='worker failed after rejection').status_code == 200
    with factory() as db:
        observation = db.get(Observation,heads[0]['id'])
        assert observation.crop_review_state == 'rejected'
        assert observation.recognition_state == 'not_requested' and observation.error is None
    assert client.get(path+'/matches').status_code == 409
    assert client.post(path+'/crop-review',json={'state':'accepted'}).status_code == 200
    assert client.post(f"/api/photos/{photo['id']}/recognize").json() == {'queued':1}


def test_confirmed_identity_requires_removal_before_rejecting_crop(api):
    client, _, _ = api
    _, heads, _ = detect(client)
    bear = client.post('/api/bears',json={'name':'Known'}).json()
    path = f"/api/heads/{heads[0]['id']}"
    assert client.post(path+'/review',json={'state':'confirmed','bear_id':bear['id']}).status_code == 200
    assert client.post(path+'/crop-review',json={'state':'rejected'}).status_code == 409
    assert client.post(path+'/review',json={'state':'unresolved'}).status_code == 200
    assert client.post(path+'/crop-review',json={'state':'rejected'}).status_code == 200


def test_correction_rename_history_and_immutable_snapshots(api):
    client, factory, _ = api
    photo, heads, _ = detect(client)
    recognize(client, photo, heads)
    first = client.post('/api/bears', json={}).json()
    other = client.post('/api/bears', json={'name': 'Other'}).json()
    path = f"/api/heads/{heads[0]['id']}"
    assert client.post(path + '/review', json={'state': 'confirmed', 'bear_id': first['id']}).status_code == 200
    later, queries, _ = detect(client, color='gray')
    recognize(client, later, queries)
    qpath = f"/api/heads/{queries[0]['id']}"
    before = client.get(f"/api/photos/{later['id']}").json()['heads'][0]['suggestions'][0]
    assert before['candidates'][0]['bear_id'] == first['id']
    assert client.patch(f"/api/bears/{first['id']}", json={'name': 'Named'}).json()['id'] == first['id']
    client.post(path + '/review', json={'state': 'confirmed', 'bear_id': other['id']})
    after = client.post(qpath + '/refresh').json()['suggestions']
    assert after[0]['candidates'][0]['bear_id'] == other['id']
    assert after[1] == before
    assert len(client.get(path + '/history').json()) == 2
    assert client.get(f"/api/bears/{first['id']}/references").json() == []
    client.post(path + '/review', json={'state': 'unusable'})
    assert client.post(qpath + '/refresh').json()['suggestions'][0]['candidates'] == []


def test_partial_failure_retry_keeps_successful_head(api):
    client, factory, _ = api
    photo, heads, _ = detect(client, boxes=[[1, 2, 40, 50, .9], [45, 3, 80, 60, .8]])
    client.post(f"/api/photos/{photo['id']}/recognize")
    job = claim(client, 'recognition')
    assert submit(client, job, heads=[{'observation_id': heads[0]['id'], 'embedding': VECTOR},
        {'observation_id': heads[1]['id'], 'embedding': [0.0] * 512}]).status_code == 200
    assert client.post(f"/api/photos/{photo['id']}/recognize").json()['queued'] == 1
    retry = claim(client, 'recognition')
    assert [h['observation_id'] for h in retry['heads']] == [heads[1]['id']]
    assert submit(client, retry, heads=[{'observation_id': heads[1]['id'], 'embedding': VECTOR}]).status_code == 200
    with factory() as db:
        assert len(db.scalars(select(Suggestion)).all()) == 2


def test_lease_reclaim_stale_result_and_bounded_retries(api):
    client, factory, _ = api
    upload(client)
    old = claim(client)
    with factory.begin() as db:
        db.get(Job, old['job_id']).lease_until = now() - timedelta(seconds=1)
    new = claim(client)
    assert new['token'] != old['token'] and new['attempt'] == 2
    assert submit(client, old, error='stale').status_code == 409
    assert submit(client, new, error='failure').status_code == 200
    last = claim(client)
    assert last['attempt'] == 3
    submit(client, last, error='failure')
    assert claim(client) is None
    assert client.post(f"/api/jobs/{last['job_id']}/retry").status_code == 200
    assert client.post(f"/api/jobs/{last['job_id']}/retry").status_code == 409
    with factory() as db:
        assert len(db.scalars(select(Attempt)).all()) == 3
    assert claim(client)['attempt'] == 1


def test_concurrent_claims_and_recognition_are_singleton(api):
    client, factory, _ = api
    upload(client)
    with ThreadPoolExecutor(max_workers=4) as pool:
        claimed = list(pool.map(lambda _: claim(client), range(4)))
    jobs = [j for j in claimed if j]
    assert len(jobs) == 1
    job = jobs[0]
    submit(client, job, body_detection={'width':100, 'height':80, 'detections':[
        {'category':1, 'confidence':.95, 'bbox':[0,0,1,1]}]})
    head_job = claim(client, 'head_detection')
    submit(client, head_job, head_detections=[{'body_index':0, 'width':100, 'height':80,
        'boxes':[[1,2,40,50,.9]]}])
    head = client.get(f"/api/photos/{job['photo_id']}").json()['heads'][0]
    client.post(f"/api/heads/{head['id']}/crop-review", json={'state':'accepted'})
    with ThreadPoolExecutor(max_workers=4) as pool:
        queued = list(pool.map(lambda _: client.post(f"/api/photos/{job['photo_id']}/recognize").json()['queued'], range(4)))
    assert sorted(queued) == [0, 0, 0, 1]


def test_worker_auth_pipeline_and_result_validation(api):
    client, _, _ = api
    assert client.post('/internal/jobs/claim', json={'stage': 'body_detection', 'pipeline': 'mock-v1'}).status_code == 401
    assert client.post('/internal/jobs/claim', headers=AUTH, json={'stage': 'body_detection', 'pipeline': 'real-v1'}).status_code == 409
    upload(client)
    job = claim(client)
    assert submit(client, job, body_detection={'width':90, 'height':80,'detections':[]}).status_code == 422
    assert submit(client, job, body_detection={'width':100,'height':80,'detections':[
        {'category':1,'confidence':.95,'bbox':[0,0,2,1]}]}).status_code == 422


def test_heartbeat_timeout_and_recovery(api):
    client, factory, _ = api
    upload(client)
    job = claim(client)
    heartbeat = f"/internal/jobs/{job['job_id']}/heartbeat"
    assert client.post(heartbeat, headers=AUTH, json={'token': 'wrong'}).status_code == 409
    assert client.post(heartbeat, headers=AUTH, json={'token': job['token']}).status_code == 200
    with factory.begin() as db:
        db.get(Job, job['job_id']).started_at = now() - timedelta(seconds=1801)
    assert client.post(heartbeat, headers=AUTH, json={'token': job['token']}).status_code == 409
    replacement = claim(client)
    assert replacement['attempt'] == 2
    assert replacement['token'] != job['token']


def test_reject_wrong_provenance_and_unrelated_heads(api):
    client, factory, _ = api
    photo, heads, _ = detect(client)
    client.post(f"/api/photos/{photo['id']}/recognize")
    job = claim(client, 'recognition')
    response = client.post(f"/internal/jobs/{job['job_id']}/result", headers=AUTH, json={
        'token': job['token'], 'pipeline': 'mock-v1', 'provenance': {'mode': 'real'}, 'heads': []})
    assert response.status_code == 409
    assert submit(client, job, heads=[{'observation_id': 'unrelated', 'embedding': VECTOR}]).status_code == 422
    assert submit(client, job, heads=[{'observation_id': heads[0]['id'], 'embedding': VECTOR}] * 2).status_code == 422
    # An ignored head cannot become a reference through a result racing with review.
    client.post(f"/api/heads/{heads[0]['id']}/review", json={'state': 'ignored'})
    assert submit(client, job, heads=[{'observation_id': heads[0]['id'], 'embedding': VECTOR}]).status_code == 200
    with factory() as db:
        head = db.get(Observation, heads[0]['id'])
        assert head.embedding is None
        assert head.recognition_state == 'not_requested'


def test_cross_origin_mutations_are_rejected(api):
    client, factory, _ = api
    # Multipart requests need no CORS preflight; reject before upload side effects.
    response = client.post('/api/photos', headers={'Origin': 'https://attacker.invalid'},
        files={'files': ('bad.png', b'anything', 'image/png')})
    assert response.status_code == 403
    assert client.post('/api/bears', headers={'Origin': 'null'}, json={}).status_code == 403
    assert client.post('/api/bears', headers={'Origin': 'http://localhost:5173'}, json={}).status_code == 200
    # CLI and worker clients omit Origin and still use the separate worker credential.
    assert client.post('/internal/jobs/claim', headers=AUTH,
        json={'stage': 'body_detection', 'pipeline': 'mock-v1'}).status_code == 200
    with factory() as db:
        assert db.scalars(select(Photo)).all() == []
