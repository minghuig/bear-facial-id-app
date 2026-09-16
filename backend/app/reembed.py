"""Queue an explicit, scoped model upgrade using persisted accepted head crops.

Run with API and workers stopped. Existing identities, photos, review history and
old immutable suggestions remain; only the active vectors are regenerated.
"""

import argparse
import json
from collections import defaultdict

from sqlalchemy import select

from .config import settings
from .db import Session
from .embedding_spaces import CURRENT_REAL_SPACE, LEGACY_REAL_SPACE
from .models import Gallery, Job, Observation


def summary(db):
    heads = db.scalars(select(Observation).order_by(Observation.id)).all()
    jobs = db.scalars(select(Job).where(Job.state.in_(['queued', 'running']))).all()
    return {
        'old_complete': sum(h.embedding_space == LEGACY_REAL_SPACE and
                            h.recognition_state == 'complete' and h.embedding is not None
                            for h in heads),
        'new_complete': sum(h.embedding_space == CURRENT_REAL_SPACE and
                            h.recognition_state == 'complete' and h.embedding is not None
                            for h in heads),
        'new_failed': sum(h.embedding_space == CURRENT_REAL_SPACE and
                          h.recognition_state == 'failed' for h in heads),
        'new_pending': sum(h.embedding_space == CURRENT_REAL_SPACE and
                           h.recognition_state in ('queued', 'running') for h in heads),
        'active_jobs': len(jobs),
        'heads': len(heads),
    }


def queue_upgrade(db, org_id, pipeline, expected):
    if not pipeline.startswith('real-v1-'):
        raise ValueError('Only a content-derived real pipeline can upgrade embeddings')
    db.info['org_id'] = org_id
    active = db.scalars(select(Job).where(Job.state.in_(['queued', 'running']))).all()
    if active:
        raise ValueError('Stop all writers and resolve active jobs before re-embedding')
    heads = db.scalars(select(Observation).where(
        Observation.embedding_space == LEGACY_REAL_SPACE,
        Observation.embedding.is_not(None)).order_by(Observation.id).with_for_update()).all()
    if len(heads) != expected:
        raise ValueError(f'Expected {expected} legacy vectors; found {len(heads)}')
    for head in heads:
        if head.recognition_state != 'complete' or head.crop_review_state != 'accepted' or not head.crop_key:
            raise ValueError('Legacy vector is not on a completed accepted crop')
        if head.review_state in ('ignored', 'unusable'):
            raise ValueError('Legacy vector is on an excluded sighting; resolve separately')
    gallery = db.scalar(select(Gallery).with_for_update())
    if gallery is None:
        raise ValueError('Organization gallery is missing')
    by_photo = defaultdict(list)
    for head in heads:
        by_photo[head.photo_id].append(head.id)
        head.embedding = None
        head.embedding_space = CURRENT_REAL_SPACE
        head.diagnostics = {}
        head.recognition_state = 'queued'
        head.error = None
        if head.review_state in ('confirmed', 'unresolved'):
            gallery.revision += 1
    for photo_id, ids in by_photo.items():
        db.add(Job(org_id=org_id, photo_id=photo_id, stage='recognition',
                   pipeline=pipeline, observation_ids=ids))
    return {'queued_heads': len(heads), 'queued_jobs': len(by_photo),
            'embedding_space': CURRENT_REAL_SPACE, 'pipeline': pipeline}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['plan', 'queue', 'verify'])
    parser.add_argument('--org', required=True, help='Exact organization id to upgrade')
    parser.add_argument('--expected', type=int, help='Required legacy vector count for queue')
    args = parser.parse_args()
    if args.action == 'queue' and (args.expected is None or args.expected < 0):
        parser.error('queue requires --expected from the read-only plan')
    with Session() as db:
        db.info['org_id'] = args.org
        if args.action == 'queue':
            result = queue_upgrade(db, args.org, settings().pipeline, args.expected)
            db.commit()
        else:
            result = summary(db)
            db.rollback()
    print(json.dumps({'org_id': args.org, **result}, sort_keys=True))


if __name__ == '__main__':
    main()
