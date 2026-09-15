"""Retrieval tests use SQLite only for filtering; queue tests require PostgreSQL."""
import math
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base, Batch, Photo, Observation, Bear, Gallery
from app.retrieval import candidates, snapshot, vector

V = [1.0] + [0.0] * 511

@pytest.mark.parametrize('value', [None, [], [0.0]*512, [1.0]*512, [float('nan')]+[0.0]*511, [float('inf')]+[0.0]*511, [[1.0]*512]])
def test_invalid_embeddings(value):
    with pytest.raises((ValueError, TypeError)):
        vector(value)


def test_eligibility_ranks_individual_sightings_and_keeps_top_ten():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        batch = Batch(); db.add(batch); db.flush()
        def photo(n):
            p = Photo(batch_id=batch.id, sha256=str(n), filename='x', original_key='x', oriented_key='x', width=100, height=100, pipeline='mock-v1')
            db.add(p); db.flush(); return p
        query_photo, other_photo = photo(1), photo(2)
        def head(p, index, bear=None, state='confirmed', pipeline='mock-v1', embedding=None):
            o = Observation(photo_id=p.id, index=index, box=[0,0,1,1], crop_key='x', pipeline=pipeline,
                bear_id=bear.id if bear else None, review_state=state, embedding=embedding if embedding is not None else V,
                recognition_state='complete')
            db.add(o); db.flush(); return o
        bears = [Bear(name=str(i)) for i in range(10)]; db.add_all(bears); db.flush()
        query = head(query_photo, 0, bears[0])
        head(query_photo, 1, bears[1]) # Same original, different head excluded.
        head(other_photo, 0, bears[2], state='unresolved')
        head(other_photo, 1, bears[3], state='ignored')
        head(other_photo, 2, bears[4], state='unusable')
        head(other_photo, 3, bears[5], pipeline='real-v1')
        head(other_photo, 4, bears[6], embedding=[0.0]*512)
        second = head(other_photo, 5, bears[7], embedding=[.8,.6]+[0.0]*510)
        best = head(other_photo, 6, bears[7])
        third = head(other_photo, 7, bears[8], embedding=[.6,.8]+[0.0]*510)
        gallery = Gallery(id=1, revision=17); db.add(gallery)
        result = snapshot(db, query, gallery)
        assert [c['bear_id'] for c in result.candidates] == [
            bears[7].id, bears[7].id, bears[8].id]
        assert [c['reference_id'] for c in result.candidates] == [best.id, second.id, third.id]
        assert result.candidates[0]['cosine'] == 1.0
        assert result.gallery_revision == 17
        for i in range(12):
            b = Bear(name='extra'); db.add(b); db.flush(); head(other_photo, 8+i, b)
        assert len(snapshot(db, query, gallery).candidates) == 10


def test_candidates_include_unassigned_sightings_and_preserve_snapshot_compatibility():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        batch = Batch(); db.add(batch); db.flush()
        def photo(n):
            p = Photo(batch_id=batch.id, sha256=str(n), filename=f'{n}.jpg', original_key='x',
                oriented_key='x', width=100, height=100, pipeline='mock-v1')
            db.add(p); db.flush(); return p
        query_photo, known_photo, unknown_photo = photo(1), photo(2), photo(3)
        bear = Bear(name='Cedar'); db.add(bear); db.flush()
        query = Observation(photo_id=query_photo.id, index=0, box=[0,0,1,1], crop_key='q',
            pipeline='mock-v1', review_state='unresolved', bear_id=None, embedding=V,
            recognition_state='complete')
        known = Observation(photo_id=known_photo.id, index=0, box=[0,0,1,1], crop_key='known',
            pipeline='mock-v1', review_state='confirmed', bear_id=bear.id, embedding=V,
            recognition_state='complete')
        unknown = Observation(photo_id=unknown_photo.id, index=0, box=[0,0,1,1], crop_key='unknown',
            pipeline='mock-v1', review_state='unresolved', bear_id=None,
            embedding=[.8,.6]+[0.0]*510, recognition_state='complete')
        db.add_all([query, known, unknown]); db.flush()

        live = candidates(db, query)
        assert live == [
            {'kind':'bear', 'id':bear.id, 'bear_id':bear.id, 'name':'Cedar',
             'reference_id':known.id, 'cosine':1.0},
            {'kind':'sighting', 'id':unknown.id, 'bear_id':None, 'name':None,
             'reference_id':unknown.id, 'cosine':.8},
        ]

        gallery = Gallery(id=1, revision=4); db.add(gallery)
        saved = snapshot(db, query, gallery)
        assert saved.candidates == live


def test_candidates_scope_worker_reads_to_query_organization():
    engine = create_engine('sqlite://')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        def head(org_id, sha, embedding):
            batch = Batch(org_id=org_id); db.add(batch); db.flush()
            photo = Photo(org_id=org_id, batch_id=batch.id, sha256=sha, filename=f'{sha}.jpg',
                original_key='x', oriented_key='x', width=100, height=100, pipeline='mock-v1')
            db.add(photo); db.flush()
            observation = Observation(org_id=org_id, photo_id=photo.id, index=0, box=[0,0,1,1],
                crop_key='x', pipeline='mock-v1', review_state='unresolved', bear_id=None,
                embedding=embedding, recognition_state='complete')
            db.add(observation); db.flush(); return observation

        query = head('internal-testing', 'query', V)
        local = head('internal-testing', 'local', [.8,.6]+[0.0]*510)
        head('other-organization', 'closer-cross-org', V)

        assert [candidate['reference_id'] for candidate in candidates(db, query)] == [local.id]
