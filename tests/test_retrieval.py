"""Retrieval tests use SQLite only for filtering; queue tests require PostgreSQL."""
import math
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models import Base, Batch, Photo, Observation, Bear, Gallery
from app.retrieval import snapshot, vector

V = [1.0] + [0.0] * 511

@pytest.mark.parametrize('value', [None, [], [0.0]*512, [1.0]*512, [float('nan')]+[0.0]*511, [float('inf')]+[0.0]*511, [[1.0]*512]])
def test_invalid_embeddings(value):
    with pytest.raises((ValueError, TypeError)):
        vector(value)


def test_eligibility_distinct_bears_and_best_reference():
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
        head(other_photo, 5, bears[7], embedding=[.8,.6]+[0.0]*510)
        best = head(other_photo, 6, bears[7])
        head(other_photo, 7, bears[8], embedding=[.6,.8]+[0.0]*510)
        gallery = Gallery(id=1, revision=17); db.add(gallery)
        result = snapshot(db, query, gallery)
        assert [c['bear_id'] for c in result.candidates] == [bears[7].id, bears[8].id]
        assert result.candidates[0]['reference_id'] == best.id
        assert result.candidates[0]['cosine'] == 1.0
        assert result.gallery_revision == 17
        for i in range(5):
            b = Bear(name='extra'); db.add(b); db.flush(); head(other_photo, 8+i, b)
        assert len(snapshot(db, query, gallery).candidates) == 5
