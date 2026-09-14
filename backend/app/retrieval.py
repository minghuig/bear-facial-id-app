import numpy as np
from sqlalchemy import select
from .models import Observation, Bear, Gallery, Suggestion

def vector(value):
    a = np.asarray(value, dtype=np.float64)
    if a.shape != (512,) or not np.isfinite(a).all() or not np.isclose(np.linalg.norm(a), 1, atol=1e-4):
        raise ValueError('Expected finite, nonzero, L2-normalized 512-dimensional embedding')
    return a

def candidates(db, query):
    q = vector(query.embedding)
    refs = db.scalars(select(Observation).where(
        Observation.org_id == query.org_id, Observation.review_state.in_(['confirmed', 'unresolved']),
        Observation.pipeline == query.pipeline, Observation.photo_id != query.photo_id,
        Observation.id != query.id, Observation.embedding.is_not(None))).all()
    best = {}
    for ref in refs:
        known = ref.review_state == 'confirmed' and ref.bear_id is not None
        unknown = ref.review_state == 'unresolved' and ref.bear_id is None
        if not known and not unknown:
            continue
        try: score = float(np.clip(q @ vector(ref.embedding), -1, 1))
        except (ValueError, TypeError): continue
        if known:
            bear = db.get(Bear, ref.bear_id)
            if bear is None:
                continue
            key = ('bear', ref.bear_id)
            candidate = {'kind':'bear', 'id':ref.bear_id, 'bear_id':ref.bear_id,
                         'name':bear.name, 'reference_id':ref.id, 'cosine':score}
        else:
            key = ('sighting', ref.id)
            candidate = {'kind':'sighting', 'id':ref.id, 'bear_id':None, 'name':None,
                         'reference_id':ref.id, 'cosine':score}
        if key not in best or score > best[key]['cosine']:
            best[key] = candidate
    return sorted(best.values(), key=lambda c: (-c['cosine'], c['kind'], c['id']))

def snapshot(db, query, gallery):
    row = Suggestion(org_id=query.org_id, observation_id=query.id, pipeline=query.pipeline,
                     gallery_revision=gallery.revision,
                     candidates=candidates(db, query)[:5])
    db.add(row)
    return row
