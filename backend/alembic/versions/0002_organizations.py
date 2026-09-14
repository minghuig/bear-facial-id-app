"""Move existing library into Internal Testing; start McNeil empty."""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'

def upgrade():
    op.create_table('organizations', sa.Column('id',sa.String(36),primary_key=True), sa.Column('name',sa.String(120),nullable=False))
    op.execute("INSERT INTO organizations (id,name) VALUES ('internal-testing','Internal Testing'), ('mcneil','McNeil')")
    op.create_table('users', sa.Column('id',sa.String(36),primary_key=True), sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('google_sub',sa.String(255),nullable=False,unique=True), sa.Column('email',sa.String(320),nullable=False))
    op.create_table('memberships', sa.Column('org_id',sa.String(36),sa.ForeignKey('organizations.id'),primary_key=True),
        sa.Column('email',sa.String(320),primary_key=True), sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=True))
    op.create_table('login_sessions', sa.Column('token_hash',sa.String(64),primary_key=True),
        sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('org_id',sa.String(36),sa.ForeignKey('organizations.id'),nullable=False),
        sa.Column('csrf',sa.String(64),nullable=False), sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False))
    for table in ('batches','photos','observations','bears','reviews','gallery','suggestions','jobs','attempts'):
        op.add_column(table, sa.Column('org_id',sa.String(36),nullable=False,server_default='internal-testing'))
        op.create_index(f'ix_{table}_org_id',table,['org_id'])
        op.alter_column(table,'org_id',server_default=None)
    op.drop_constraint('photos_sha256_key','photos',type_='unique')
    op.create_unique_constraint('uq_photos_org_sha','photos',['org_id','sha256'])
    op.execute("INSERT INTO gallery (id,revision,org_id) VALUES (2,0,'mcneil')")

def downgrade():
    raise RuntimeError('Organization migration is forward-only; never collapse separate libraries')
