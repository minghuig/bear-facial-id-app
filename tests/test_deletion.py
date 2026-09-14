from sqlalchemy import select

from app.models import Attempt, Batch, Bear, Gallery, Job, Observation, Photo, Review, Suggestion
from test_workflow import detect


def test_delete_photo_removes_database_records_and_stored_images(api):
    client, factory, objects = api
    photo, heads, _ = detect(client)
    bear = client.post('/api/bears', json={'name':'Temporary bear'}).json()
    assert client.post(f"/api/heads/{heads[0]['id']}/review", json={
        'state':'confirmed', 'bear_id':bear['id']}).status_code == 200
    assert client.get(f"/api/photos/{photo['id']}/image?variant=thumbnail-v1").status_code == 200
    assert client.get(f"/api/heads/{heads[0]['id']}/image?variant=preview-v1").status_code == 200
    assert objects

    response = client.delete(f"/api/photos/{photo['id']}")
    assert response.status_code == 200, response.text
    assert response.json() == {'deleted':True, 'heads_deleted':1}
    assert objects == {}
    assert client.get(f"/api/photos/{photo['id']}").status_code == 404
    assert client.get(f"/api/heads/{heads[0]['id']}/image").status_code == 404

    with factory() as db:
        assert db.get(Photo, photo['id']) is None
        assert db.get(Observation, heads[0]['id']) is None
        assert db.scalars(select(Job).where(Job.photo_id == photo['id'])).all() == []
        assert db.scalars(select(Attempt)).all() == []
        assert db.scalars(select(Review).where(Review.observation_id == heads[0]['id'])).all() == []
        assert db.scalars(select(Batch)).all() == []
        assert db.get(Bear, bear['id']) is not None
        assert db.get(Gallery, 1).revision == 2


def test_delete_bear_requires_no_associated_photos_and_scrubs_saved_candidates(api):
    client, factory, _ = api
    photo, heads, _ = detect(client)
    bear = client.post('/api/bears', json={'name':'Bad name'}).json()
    assert client.post(f"/api/heads/{heads[0]['id']}/review", json={
        'state':'confirmed', 'bear_id':bear['id']}).status_code == 200
    with factory.begin() as db:
        db.add(Suggestion(observation_id=heads[0]['id'], pipeline='mock-v1', gallery_revision=1,
            candidates=[{'kind':'bear', 'id':bear['id'], 'bear_id':bear['id'],
                         'name':'Bad name', 'reference_id':heads[0]['id'], 'cosine':.9}]))

    listed = client.get('/api/bears').json()[0]
    assert listed['photo_count'] == 1
    blocked = client.delete(f"/api/bears/{bear['id']}")
    assert blocked.status_code == 409
    assert '1 associated photo' in blocked.json()['detail']
    with factory() as db:
        assert db.get(Bear, bear['id']) is not None
        assert db.get(Observation, heads[0]['id']).bear_id == bear['id']

    assert client.post(f"/api/heads/{heads[0]['id']}/review", json={
        'state':'unresolved', 'bear_id':None}).status_code == 200
    assert client.get('/api/bears').json()[0]['photo_count'] == 0
    response = client.delete(f"/api/bears/{bear['id']}")
    assert response.status_code == 200, response.text
    assert response.json() == {'deleted':True}
    assert client.get('/api/bears').json() == []
    detail = client.get(f"/api/photos/{photo['id']}").json()
    assert detail['heads'][0]['review_state'] == 'unresolved'
    assert detail['heads'][0]['bear_id'] is None
    assert detail['heads'][0]['suggestions'][0]['candidates'] == []

    with factory() as db:
        assert db.get(Bear, bear['id']) is None
        history = db.scalars(select(Review).where(
            Review.observation_id == heads[0]['id'])).all()
        assert [(review.state, review.bear_id) for review in history] == [('unresolved', None)]
        assert db.get(Gallery, 1).revision == 3


def test_cross_origin_deletes_are_rejected(api):
    client, _, _ = api
    photo, _, _ = detect(client)
    response = client.delete(f"/api/photos/{photo['id']}",
                             headers={'Origin':'https://attacker.invalid'})
    assert response.status_code == 403
    assert client.get(f"/api/photos/{photo['id']}").status_code == 200
