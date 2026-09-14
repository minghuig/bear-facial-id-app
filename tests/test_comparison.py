import math
import uuid
from datetime import timedelta

import pytest

from app.models import Attempt, Batch, Bear, Gallery, Job, Observation, Photo, Review, now


VECTOR = [1.0] + [0.0] * 511


def unit(x):
    return [x, math.sqrt(1 - x * x)] + [0.0] * 510


def seed_head(db, *, filename, embedding=VECTOR, state='unresolved', bear=None,
              pipeline='mock-v1', photo=None, index=0):
    if photo is None:
        batch = Batch(); db.add(batch); db.flush()
        photo = Photo(batch_id=batch.id, sha256=uuid.uuid4().hex, filename=filename,
            original_key=f'photos/{filename}', oriented_key=f'oriented/{filename}',
            width=100, height=80, detection_state='complete', pipeline=pipeline)
        db.add(photo); db.flush()
    head = Observation(photo_id=photo.id, index=index, box=[1,2,30,40],
        crop_key=f'crops/{filename}/{index}', pipeline=pipeline,
        recognition_state='complete', review_state=state,
        bear_id=bear.id if bear else None, embedding=embedding)
    db.add(head); db.flush()
    return head


def test_live_matches_include_unknowns_and_complete_identity_gallery(api):
    client, factory, _ = api
    with factory.begin() as db:
        cedar = Bear(name='Cedar'); db.add(cedar); db.flush()
        query = seed_head(db, filename='query.jpg')
        support = seed_head(db, filename='best.jpg', embedding=unit(.8),
            state='confirmed', bear=cedar)
        other = seed_head(db, filename='other.jpg', embedding=unit(.6),
            state='confirmed', bear=cedar)
        unknown = seed_head(db, filename='unknown.jpg', embedding=unit(.7))
        seed_head(db, filename='ignored.jpg', embedding=unit(.99), state='ignored')
        seed_head(db, filename='bad.jpg', embedding=[0.0] * 512)
        seed_head(db, filename='other-pipeline.jpg', embedding=VECTOR, pipeline='real-v1')
        seed_head(db, filename='same-original.jpg', embedding=VECTOR,
            state='confirmed', bear=cedar, photo=db.get(Photo, query.photo_id), index=1)

    response = client.get(f'/api/heads/{query.id}/matches')
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['head'] == {
        'id': query.id,
        'review_state': 'unresolved',
        'bear_id': None,
        'crop_url': f'/api/heads/{query.id}/image?variant=preview-v1',
    }
    assert [(candidate['kind'], candidate['id'], candidate['reference_id'])
            for candidate in body['candidates']] == [
        ('bear', cedar.id, support.id),
        ('sighting', unknown.id, unknown.id),
    ]
    known = body['candidates'][0]
    assert known['label'] == 'Cedar'
    assert known['similarity'] == .8
    assert known['bear_id'] == cedar.id
    assert [photo['id'] for photo in known['photos']] == [support.id, other.id]
    assert [photo['label'] for photo in known['photos']] == ['best.jpg', 'other.jpg']
    assert body['candidates'][1]['photos'] == [{
        'id': unknown.id,
        'src': f'/api/heads/{unknown.id}/image?variant=preview-v1',
        'label': 'unknown.jpg',
    }]


def test_match_two_unassigned_sightings_creates_one_unnamed_identity(api):
    client, factory, _ = api
    with factory.begin() as db:
        source = seed_head(db, filename='source.jpg')
        reference = seed_head(db, filename='reference.jpg', embedding=unit(.9))

    response = client.post(f'/api/heads/{source.id}/match', json={
        'reference_id': reference.id,
        'expected_bear_id': None,
        'expected_review_state': 'unresolved',
        'expected_reference_bear_id': None,
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['head']['id'] == source.id
    assert body['head']['review_state'] == 'confirmed'
    assert body['head']['bear_id'] is not None
    assert body['undo']['head_review_id']
    assert body['undo']['reference_review_id']

    with factory() as db:
        saved_source = db.get(Observation, source.id)
        saved_reference = db.get(Observation, reference.id)
        assert saved_source.bear_id == saved_reference.bear_id == body['head']['bear_id']
        assert saved_source.review_state == saved_reference.review_state == 'confirmed'
        assert db.get(Bear, saved_source.bear_id).name is None
        assert db.get(Gallery, 1).revision == 1
        reviews = db.query(Review).order_by(Review.created_at).all()
        assert [(review.observation_id, review.state, review.bear_id) for review in reviews] == [
            (source.id, 'confirmed', saved_source.bear_id),
            (reference.id, 'confirmed', saved_source.bear_id),
        ]

    undone = client.post(f'/api/heads/{source.id}/undo-match', json=body['undo'])
    assert undone.status_code == 200, undone.text
    assert undone.json()['review_state'] == 'unresolved'
    assert undone.json()['bear_id'] is None
    with factory() as db:
        assert db.get(Observation, source.id).bear_id is None
        assert db.get(Observation, reference.id).bear_id is None
        assert db.get(Observation, reference.id).review_state == 'unresolved'
        assert db.get(Bear, body['head']['bear_id']) is not None


def test_reassign_moves_only_source_and_undo_restores_original_identity(api):
    client, factory, _ = api
    with factory.begin() as db:
        old = Bear(name='Old group')
        destination = Bear(name='Destination')
        db.add_all([old, destination]); db.flush()
        source = seed_head(db, filename='source.jpg', state='confirmed', bear=old)
        peer = seed_head(db, filename='peer.jpg', state='confirmed', bear=old)
        reference = seed_head(db, filename='target.jpg', state='confirmed', bear=destination)
        db.add(Review(observation_id=source.id, state='confirmed', bear_id=old.id))

    matched = client.post(f'/api/heads/{source.id}/match', json={
        'reference_id': reference.id,
        'expected_bear_id': old.id,
        'expected_review_state': 'confirmed',
        'expected_reference_bear_id': destination.id,
    })
    assert matched.status_code == 200, matched.text
    undo = matched.json()['undo']
    assert undo['reference_review_id'] is None
    with factory() as db:
        assert db.get(Observation, source.id).bear_id == destination.id
        assert db.get(Observation, peer.id).bear_id == old.id
        assert db.get(Observation, reference.id).bear_id == destination.id

    undone = client.post(f'/api/heads/{source.id}/undo-match', json=undo)
    assert undone.status_code == 200, undone.text
    assert undone.json()['bear_id'] == old.id
    assert undone.json()['review_state'] == 'confirmed'
    with factory() as db:
        assert db.get(Observation, source.id).bear_id == old.id
        assert db.get(Observation, peer.id).bear_id == old.id
        assert db.get(Observation, reference.id).bear_id == destination.id
        assert db.get(Gallery, 1).revision == 2
        history = db.query(Review).filter(Review.observation_id == source.id).order_by(Review.created_at).all()
        assert [(review.state, review.bear_id) for review in history] == [
            ('confirmed', old.id),
            ('confirmed', destination.id),
            ('confirmed', old.id),
        ]


def test_recognized_unassigned_sighting_advances_gallery_revision(api):
    client, factory, _ = api
    token = 'comparison-result-token'
    with factory.begin() as db:
        head = seed_head(db, filename='new.jpg', embedding=None)
        head.recognition_state = 'running'
        job = Job(photo_id=head.photo_id, stage='recognition', pipeline='mock-v1',
            observation_ids=[head.id], state='running', attempts=1, token=token,
            started_at=now(), lease_until=now() + timedelta(minutes=1))
        db.add(job); db.flush()
        db.add(Attempt(job_id=job.id, token=token))

    response = client.post(f'/internal/jobs/{job.id}/result', headers={
        'Authorization': 'Bearer test-worker-token-at-least-24-characters'}, json={
        'token': token,
        'pipeline': 'mock-v1',
        'provenance': {'mode': 'mock'},
        'heads': [{'observation_id': head.id, 'embedding': VECTOR}],
    })
    assert response.status_code == 200, response.text
    with factory() as db:
        assert db.get(Observation, head.id).embedding == VECTOR
        assert db.get(Gallery, 1).revision == 1


def test_match_requires_explicit_expected_values(api):
    client, factory, _ = api
    with factory.begin() as db:
        source = seed_head(db, filename='source.jpg')
        reference = seed_head(db, filename='reference.jpg')
    response = client.post(f'/api/heads/{source.id}/match', json={
        'reference_id': reference.id,
    })
    assert response.status_code == 422


def test_match_rejects_stale_source_or_target_identity(api):
    client, factory, _ = api
    with factory.begin() as db:
        source_bear = Bear(name='Source')
        target_bear = Bear(name='Target')
        stale_bear = Bear(name='Stale')
        db.add_all([source_bear, target_bear, stale_bear]); db.flush()
        source = seed_head(db, filename='source.jpg', state='confirmed', bear=source_bear)
        reference = seed_head(db, filename='target.jpg', state='confirmed', bear=target_bear)
    base = {
        'reference_id': reference.id,
        'expected_bear_id': source_bear.id,
        'expected_review_state': 'confirmed',
        'expected_reference_bear_id': target_bear.id,
    }
    assert client.post(f'/api/heads/{source.id}/match', json={
        **base, 'expected_review_state': 'unresolved'}).status_code == 409
    assert client.post(f'/api/heads/{source.id}/match', json={
        **base, 'expected_bear_id': stale_bear.id}).status_code == 409
    assert client.post(f'/api/heads/{source.id}/match', json={
        **base, 'expected_reference_bear_id': stale_bear.id}).status_code == 409
    with factory() as db:
        assert db.get(Observation, source.id).bear_id == source_bear.id
        assert db.get(Gallery, 1).revision == 0


@pytest.mark.parametrize('state,with_bear', [
    ('ignored', False),
    ('unusable', False),
    ('confirmed', False),
    ('unresolved', True),
])
def test_match_rejects_reference_with_ineligible_review_state(api, state, with_bear):
    client, factory, _ = api
    with factory.begin() as db:
        bear = Bear(name='Malformed'); db.add(bear); db.flush()
        source = seed_head(db, filename='source.jpg')
        reference = seed_head(db, filename='reference.jpg', state=state,
            bear=bear if with_bear else None)
    response = client.post(f'/api/heads/{source.id}/match', json={
        'reference_id': reference.id,
        'expected_bear_id': None,
        'expected_review_state': 'unresolved',
        'expected_reference_bear_id': bear.id if with_bear else None,
    })
    assert response.status_code == 409


@pytest.mark.parametrize('difference', ['same-original', 'pipeline', 'vector'])
def test_match_rejects_incompatible_reference(api, difference):
    client, factory, _ = api
    with factory.begin() as db:
        source = seed_head(db, filename='source.jpg')
        if difference == 'same-original':
            reference = seed_head(db, filename='same.jpg', photo=db.get(Photo, source.photo_id), index=1)
        elif difference == 'pipeline':
            reference = seed_head(db, filename='pipeline.jpg', pipeline='real-v1')
        else:
            reference = seed_head(db, filename='vector.jpg', embedding=[0.0] * 512)
    response = client.post(f'/api/heads/{source.id}/match', json={
        'reference_id': reference.id,
        'expected_bear_id': None,
        'expected_review_state': 'unresolved',
        'expected_reference_bear_id': None,
    })
    assert response.status_code == 409


@pytest.mark.parametrize('edited', ['source', 'reference'])
def test_undo_refuses_a_later_review(api, edited):
    client, factory, _ = api
    with factory.begin() as db:
        source = seed_head(db, filename='source.jpg')
        reference = seed_head(db, filename='reference.jpg')
    matched = client.post(f'/api/heads/{source.id}/match', json={
        'reference_id': reference.id,
        'expected_bear_id': None,
        'expected_review_state': 'unresolved',
        'expected_reference_bear_id': None,
    })
    assert matched.status_code == 200, matched.text
    bear_id = matched.json()['head']['bear_id']
    edited_id = source.id if edited == 'source' else reference.id
    later = client.post(f'/api/heads/{edited_id}/review', json={
        'state': 'confirmed', 'bear_id': bear_id})
    assert later.status_code == 200, later.text

    response = client.post(f'/api/heads/{source.id}/undo-match', json=matched.json()['undo'])
    assert response.status_code == 409
    with factory() as db:
        assert db.get(Observation, source.id).bear_id == bear_id
        assert db.get(Observation, reference.id).bear_id == bear_id
