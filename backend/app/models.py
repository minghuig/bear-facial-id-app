import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, JSON, Integer, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def uid(): return str(uuid.uuid4())
def now(): return datetime.now(timezone.utc)
class Base(DeclarativeBase): pass
class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
class OrgScoped:
    org_id: Mapped[str] = mapped_column(String(36), default='internal-testing', index=True)

class Batch(OrgScoped, Record, Base):
    __tablename__ = 'batches'
class Photo(OrgScoped, Record, Base):
    __tablename__ = 'photos'
    batch_id: Mapped[str] = mapped_column(ForeignKey('batches.id'))
    __table_args__ = (UniqueConstraint('org_id', 'sha256'),)
    sha256: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(Text)
    original_key: Mapped[str] = mapped_column(Text)
    oriented_key: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    detection_state: Mapped[str] = mapped_column(default='queued')
    pipeline: Mapped[str] = mapped_column(Text)
    detections: Mapped[list] = mapped_column(JSON, default=list)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
class Observation(OrgScoped, Record, Base):
    __tablename__ = 'observations'
    __table_args__ = (UniqueConstraint('photo_id', 'index'),)
    photo_id: Mapped[str] = mapped_column(ForeignKey('photos.id'), index=True)
    index: Mapped[int] = mapped_column(Integer)
    box: Mapped[list] = mapped_column(JSON)
    crop_key: Mapped[str] = mapped_column(Text)
    pipeline: Mapped[str] = mapped_column(Text)
    recognition_state: Mapped[str] = mapped_column(default='not_requested')
    review_state: Mapped[str] = mapped_column(default='unresolved')
    bear_id: Mapped[str | None] = mapped_column(ForeignKey('bears.id'), nullable=True)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    diagnostics: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
class Bear(OrgScoped, Record, Base):
    __tablename__ = 'bears'
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
class Review(OrgScoped, Record, Base):
    __tablename__ = 'reviews'
    observation_id: Mapped[str] = mapped_column(ForeignKey('observations.id'), index=True)
    state: Mapped[str] = mapped_column(String)
    bear_id: Mapped[str | None] = mapped_column(ForeignKey('bears.id'), nullable=True)
class Gallery(OrgScoped, Base):
    __tablename__ = 'gallery'
    id: Mapped[int] = mapped_column(primary_key=True)
    revision: Mapped[int] = mapped_column(default=0)
class Suggestion(OrgScoped, Record, Base):
    __tablename__ = 'suggestions'
    observation_id: Mapped[str] = mapped_column(ForeignKey('observations.id'), index=True)
    pipeline: Mapped[str] = mapped_column(Text)
    gallery_revision: Mapped[int] = mapped_column(Integer)
    candidates: Mapped[list] = mapped_column(JSON)
class Job(OrgScoped, Record, Base):
    __tablename__ = 'jobs'
    photo_id: Mapped[str] = mapped_column(ForeignKey('photos.id'), index=True)
    stage: Mapped[str] = mapped_column(String)
    pipeline: Mapped[str] = mapped_column(Text)
    observation_ids: Mapped[list] = mapped_column(JSON, default=list)
    state: Mapped[str] = mapped_column(default='queued', index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    token: Mapped[str | None] = mapped_column(String, nullable=True)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
class Attempt(OrgScoped, Record, Base):
    __tablename__ = 'attempts'
    job_id: Mapped[str] = mapped_column(ForeignKey('jobs.id'), index=True)
    token: Mapped[str] = mapped_column(String, unique=True)
    state: Mapped[str] = mapped_column(default='running')
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

class Organization(Base):
    __tablename__ = 'organizations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))

class User(Record, Base):
    __tablename__ = 'users'
    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320))

class Membership(Base):
    __tablename__ = 'memberships'
    org_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey('users.id'), nullable=True)

class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    org_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'))
    csrf: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))