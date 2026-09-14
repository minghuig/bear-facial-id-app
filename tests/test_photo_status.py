from test_workflow import detect


def test_status_tracks_explicit_decisions_and_reassignment(api):
    client, _, _ = api
    photo, heads, _ = detect(client, boxes=[[1,2,40,50,.9], [45,3,80,60,.8]])
    def label():
        return client.get('/api/photos').json()[0]['status_label']
    assert label() == 'Ready to Review'
    assert client.post(f"/api/heads/{heads[0]['id']}/review", json={'state':'unresolved'}).status_code == 200
    assert label() == 'Partially reviewed (1/2) · 1 unidentified'
    bear = client.post('/api/bears', json={'name':'Test Bear'}).json()
    assert client.post(f"/api/heads/{heads[1]['id']}/review", json={'state':'confirmed','bear_id':bear['id']}).status_code == 200
    assert label() == 'Reviewed · 1 confirmed, 1 unidentified'
    client.post(f"/api/heads/{heads[1]['id']}/review", json={'state':'unresolved'})
    assert label() == 'Reviewed · 2 unidentified'


def test_processing_and_empty_photo_labels(api):
    from types import SimpleNamespace
    from app.photo_status import status
    assert status('queued', [], set()) == 'Detecting Bears…'
    assert status('running', [], set()) == 'Detecting Bears…'
    assert status('failed', [], set()) == 'Detection failed'
    assert status('complete', [], set()) == 'No bears detected'
    head = SimpleNamespace(id='1', recognition_state='running', review_state='unresolved')
    assert status('complete', [head], set()) == 'Recognizing Bears…'
    head.recognition_state = 'failed'
    assert status('complete', [head], set()) == 'Recognition failed — retry'
