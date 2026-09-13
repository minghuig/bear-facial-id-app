import numpy as np
from sqlalchemy import select
from .models import Observation, Bear, Gallery, Suggestion

def vector(value):
    a = np.asarray(value, dtype=np.float64)
    if a.shape != (512,) or not np.isfinite(a).all() or not np.isclose(np.linalg.norm(a), 1, atol=1e-4):
        raise ValueError('Expected finite, nonzero, L2-normalized 512-dimensional embedding')
    return a

def snapshot(db, query, gallery):
    q = vector(query.embedding)
    refs = db.scalars(select(Observation).where(
        Observation.review_state == 'confirmed', Observation.bear_id.is_not(None),
        Observation.pipeline == query.pipeline, Observation.photo_id != query.photo_id,
        Observation.id != query.id, Observation.embedding.is_not(None))).all()
    best = {}
    for ref in refs:
        try: score = float(np.clip(q @ vector(ref.embedding), -1, 1))
        except (ValueError, TypeError): continue
        candidate = {'bear_id':ref.bear_id, 'name':db.get(Bear, ref.bear_id).name,
                     'reference_id':ref.id, 'cosine':score}
        if ref.bear_id not in best or score > best[ref.bear_id]['cosine']:
            best[ref.bear_id] = candidate
    row = Suggestion(observation_id=query.id, pipeline=query.pipeline,
                     gallery_revision=gallery.revision,
                     candidates=sorted(best.values(), key=lambda c: (-c['cosine'], c['bear_id']))[:5])
    db.add(row)
    return row
