"""Add body detections, crop curation, and an explicit embedding space."""
import json
import os
import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'


def upgrade():
    op.add_column('photos', sa.Column('body_detections', sa.JSON(), nullable=False,
                                      server_default='[]'))
    op.alter_column('photos', 'body_detections', server_default=None)
    op.add_column('observations', sa.Column('body_index', sa.Integer(), nullable=True))
    op.add_column('observations', sa.Column('detector_score', sa.Float(), nullable=True))
    op.add_column('observations', sa.Column('embedding_space', sa.Text(), nullable=False,
        server_default='poseswin-test-on-2020-v1'))
    op.execute("UPDATE observations SET embedding_space = pipeline WHERE pipeline LIKE 'mock%'")
    op.alter_column('observations', 'embedding_space', server_default=None)
    # Existing heads were already admitted to recognition and remain valid.
    op.add_column('observations', sa.Column('crop_review_state', sa.String(), nullable=False,
                                            server_default='accepted'))
    op.alter_column('observations', 'crop_review_state', server_default=None)
    op.create_table('crop_reviews',
        sa.Column('observation_id', sa.String(36), sa.ForeignKey('observations.id'), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('org_id', sa.String(36), nullable=False))
    op.create_index('ix_crop_reviews_observation_id', 'crop_reviews', ['observation_id'])
    op.create_index('ix_crop_reviews_org_id', 'crop_reviews', ['org_id'])
    reconcile_unfinished_jobs(op.get_bind())


def reconcile_unfinished_jobs(bind):
    """Fence old tokens and requeue unfinished work under the released pipeline.

    Deployment stops the old writers and provides PIPELINE in runtime.env before
    this migration. Completed jobs/photos are history, not silently reprocessed.
    """
    active = bind.execute(sa.text("""SELECT id,photo_id,org_id,stage,token,observation_ids
        FROM jobs WHERE stage IN ('detection','recognition')
        AND state IN ('queued','running') ORDER BY created_at,id""")).mappings().all()
    if not active:
        return
    pipeline = os.environ.get('PIPELINE')
    if not pipeline:
        raise RuntimeError('PIPELINE is required to reconcile unfinished pre-upgrade jobs')
    for job in active:
        if job['token']:
            bind.execute(sa.text("""UPDATE attempts SET state='failed',
                error='Superseded by body/head pipeline upgrade' WHERE token=:token
                AND state='running'"""), {'token':job['token']})
        bind.execute(sa.text("""UPDATE jobs SET state='superseded',
            error='Superseded by body/head pipeline upgrade' WHERE id=:id"""),
            {'id':job['id']})
        if job['stage'] == 'detection':
            existing = bind.execute(sa.text(
                'SELECT 1 FROM observations WHERE photo_id=:photo_id LIMIT 1'),
                {'photo_id':job['photo_id']}).first()
            if existing:
                bind.execute(sa.text("""UPDATE photos SET detection_state='complete'
                    WHERE id=:id"""), {'id':job['photo_id']})
                continue
            stage = 'body_detection'
            observation_ids = []
            bind.execute(sa.text("""UPDATE photos SET pipeline=:pipeline,
                detection_state='queued' WHERE id=:id"""),
                {'pipeline':pipeline,'id':job['photo_id']})
        else:
            stage = 'recognition'
            observation_ids = job['observation_ids']
            bind.execute(sa.text("""UPDATE observations SET recognition_state='queued'
                WHERE photo_id=:photo_id AND recognition_state='running'"""),
                {'photo_id':job['photo_id']})
        bind.execute(sa.text("""INSERT INTO jobs
            (id,created_at,org_id,photo_id,stage,pipeline,observation_ids,state,attempts)
            VALUES (:id,:created_at,:org_id,:photo_id,:stage,:pipeline,:observation_ids,
                    'queued',0)"""), {
            'id':str(uuid.uuid4()), 'created_at':datetime.now(timezone.utc),
            'org_id':job['org_id'], 'photo_id':job['photo_id'], 'stage':stage,
            'pipeline':pipeline, 'observation_ids':json.dumps(observation_ids),
        })


def downgrade():
    raise RuntimeError('Body/head curation migration is forward-only; restore a verified backup instead')
