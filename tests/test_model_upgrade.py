"""The released six-year weights must never reuse the five-year vector space."""

import pytest
from sqlalchemy import select


def test_checkpoint_and_embedding_family_are_explicit():
    from app.embedding_spaces import CURRENT_REAL_SPACE, LEGACY_REAL_SPACE, for_pipeline
    from app import main
    assert CURRENT_REAL_SPACE == 'poseswin-katmai-6y-v1'
    assert CURRENT_REAL_SPACE != LEGACY_REAL_SPACE
    assert for_pipeline('mock-v1') == 'mock-v1'
    assert main.embedding_space('real-v1-test') == CURRENT_REAL_SPACE


def test_reembed_queues_saved_crops_without_changing_bear_links(api):
    _, factory, _ = api
    from app.embedding_spaces import CURRENT_REAL_SPACE, LEGACY_REAL_SPACE
    from app.models import Batch, Bear, Gallery, Job, Observation, Photo, Suggestion
    from app.reembed import queue_upgrade

    with factory() as db:
        batch = Batch(); bear = Bear(name='Known Bear')
        db.add_all([batch, bear]); db.flush()
        for index in range(2):
            photo = Photo(batch_id=batch.id, sha256=str(index).zfill(64),
                          filename=f'{index}.jpg', original_key=f'original/{index}',
                          oriented_key=f'oriented/{index}', width=224, height=224,
                          pipeline='real-v1-old')
            db.add(photo); db.flush()
            head = Observation(photo_id=photo.id, index=0, box=[0, 0, 224, 224],
                               crop_key=f'crops/{index}.jpg', pipeline='real-v1-old',
                               embedding_space=LEGACY_REAL_SPACE,
                               crop_review_state='accepted', recognition_state='complete',
                               review_state='confirmed' if index == 0 else 'unresolved',
                               bear_id=bear.id if index == 0 else None,
                               embedding=[1.] + [0.] * 511)
            db.add(head); db.flush()
            db.add(Suggestion(observation_id=head.id, pipeline='real-v1-old',
                              gallery_revision=0, candidates=[]))
        db.commit()

    with factory() as db:
        queued = queue_upgrade(db, 'internal-testing', 'real-v1-six-year', 2)
        assert queued['queued_heads'] == queued['queued_jobs'] == 2
        db.commit()

    with factory() as db:
        heads = db.scalars(select(Observation).order_by(Observation.id)).all()
        jobs = db.scalars(select(Job)).all()
        assert len(heads) == len(jobs) == 2
        assert all(h.embedding is None and h.embedding_space == CURRENT_REAL_SPACE
                   and h.recognition_state == 'queued' for h in heads)
        assert {h.bear_id for h in heads} == {None, bear.id}
        assert all(job.pipeline == 'real-v1-six-year' and job.stage == 'recognition'
                   for job in jobs)
        assert all(photo.pipeline == 'real-v1-old' for photo in db.scalars(select(Photo)))
        assert db.scalar(select(Gallery)).revision == 2
        assert len(db.scalars(select(Suggestion)).all()) == 2

    with factory() as db:
        with pytest.raises(ValueError, match='active jobs'):
            queue_upgrade(db, 'internal-testing', 'real-v1-six-year', 2)
