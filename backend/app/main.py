import hashlib
import hmac
import io
import os
from datetime import timedelta
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import delete, select, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .db import session
from .models import Batch, Photo, Observation, Bear, Review, CropReview, Gallery, Suggestion, Job, Attempt, now, uid
from .contracts import Claim, Lease, Result, ReviewInput, CropReviewInput, MatchInput, UndoMatchInput, BearInput
from . import storage, previews
from .detection import body_crop, head_crop, encode_jpeg_crop
from .embedding_spaces import for_pipeline
from .photo_status import status as photo_status
from .retrieval import MATCH_LIMIT, candidates, snapshot, vector

s = settings()
app = FastAPI(title='Only Bears', docs_url=None if s.public_deployment else '/docs', redoc_url=None if s.public_deployment else '/redoc')
def browser_origins(config):
    if (config.environment == 'local' and not config.public_deployment
            and config.cors_origin in ('http://localhost:5174', 'http://127.0.0.1:5174')):
        return ['http://localhost:5174', 'http://127.0.0.1:5174']
    return [config.cors_origin]

app.add_middleware(CORSMiddleware, allow_origins=browser_origins(s), allow_methods=['GET','POST','PATCH','DELETE'], allow_headers=['Content-Type','X-CSRF-Token','X-Organization-ID'])
@app.middleware('http')
async def restrict_browser_origin(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin and origin not in browser_origins(s):
        return JSONResponse({'detail':'Browser origin is not allowed'}, status_code=403)
    return await call_next(request)

DB = Annotated[Session, Depends(session)]

def require_worker(authorization: Annotated[str | None, Header()] = None):
    if not hmac.compare_digest(authorization or '', f'Bearer {s.worker_token}'):
        raise HTTPException(401, 'Worker credential required')

def need(db, cls, identity):
    obj = db.get(cls, identity)
    if obj is None: raise HTTPException(404, 'Not found')
    return obj

def embedding_space(pipeline):
    # Detector/crop provenance can change independently, but ReID checkpoint
    # changes must never compare vectors from two different model spaces.
    return for_pipeline(pipeline)

def lock_gallery(db):
    return db.scalar(select(Gallery).where(Gallery.org_id == db.info.get('org_id', 'internal-testing')).with_for_update())

def photo_json(p):
    return dict(id=p.id, filename=p.filename, width=p.width, height=p.height,
                detection_state=p.detection_state, pipeline=p.pipeline, created_at=p.created_at,
                image_url=f'/api/photos/{p.id}/image?variant=preview-v1',
                thumbnail_url=f'/api/photos/{p.id}/image?variant=thumbnail-v1')

def head_json(db, o):
    suggestions = db.scalars(select(Suggestion).where(Suggestion.observation_id == o.id).order_by(Suggestion.created_at.desc())).all()
    return dict(id=o.id, photo_id=o.photo_id, index=o.index, body_index=o.body_index,
                detector_score=o.detector_score, box=o.box,
                crop_url=f'/api/heads/{o.id}/image?variant=preview-v1', recognition_state=o.recognition_state,
                crop_review_state=o.crop_review_state, review_state=o.review_state,
                bear_id=o.bear_id, error=o.error,
                suggestions=[dict(id=x.id, pipeline=x.pipeline, gallery_revision=x.gallery_revision,
                                  created_at=x.created_at, candidates=x.candidates) for x in suggestions])

def queue_recognition(db, photo, heads):
    eligible = [head for head in heads if head.crop_review_state == 'accepted'
                and head.review_state not in ('ignored','unusable')
                and head.recognition_state in ('not_requested','failed')]
    if not eligible:
        return 0
    db.add(Job(photo_id=photo.id, stage='recognition', pipeline=s.pipeline,
               observation_ids=[head.id for head in eligible]))
    for head in eligible:
        head.recognition_state = 'queued'
        head.error = None
    return len(eligible)

def scrub_suggestion_candidates(db, remove):
    for suggestion in db.scalars(select(Suggestion)).all():
        kept = [candidate for candidate in suggestion.candidates if not remove(candidate)]
        if len(kept) != len(suggestion.candidates):
            suggestion.candidates = kept

@app.get('/api/status')
@app.get('/health')
def health(db: DB):
    db.execute(text('SELECT 1'))
    return {'status':'ok', 'pipeline':s.pipeline, 'environment':s.environment,
            'auto_recognize':s.auto_recognize, 'commit':os.getenv('RELEASE_COMMIT','development')}

@app.get('/api/photos')
def photos(db: DB):
    by_photo = {}
    for head in db.scalars(select(Observation)).all():
        by_photo.setdefault(head.photo_id, []).append(head)
    reviewed_ids = set(db.scalars(select(Review.observation_id).distinct()).all())
    return [{**photo_json(p), 'status_label': photo_status(p.detection_state, by_photo.get(p.id, []), reviewed_ids),
             'bear_ids': sorted({h.bear_id for h in by_photo.get(p.id, []) if h.review_state == 'confirmed' and h.bear_id})}
            for p in db.scalars(select(Photo).order_by(Photo.created_at.desc())).all()]

@app.post('/api/photos')
def upload(db: DB, files: Annotated[list[UploadFile], File()]):
    if not 1 <= len(files) <= 20: raise HTTPException(400, 'Upload 1–20 JPEG/PNG files')
    batch = Batch(); db.add(batch); db.flush()
    result = []
    for file in files:
        data = file.file.read(25 * 1024 * 1024 + 1)
        if len(data) > 25 * 1024 * 1024:
            result.append({'filename':file.filename, 'error':'File exceeds 25 MB'}); continue
        digest = hashlib.sha256(data).hexdigest()
        existing = db.scalar(select(Photo).where(Photo.sha256 == digest))
        if existing:
            result.append({**photo_json(existing), 'duplicate':True}); continue
        try:
            image = Image.open(io.BytesIO(data))
            if image.format not in ('JPEG','MPO','PNG'): raise ValueError('JPEG/PNG only')
            # Camera JPEGs may carry MPO metadata; process their primary frame.
            image.seek(0)
            image = ImageOps.exif_transpose(image).convert('RGB')
            image.load()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as e:
            result.append({'filename':file.filename, 'error':str(e)}); continue
        org = db.info.get('org_id', 'internal-testing')
        original = f'photos/{org}/{digest}/original'
        oriented = f'photos/{org}/{digest}/oriented.png'
        out = io.BytesIO(); image.save(out, format='PNG')
        storage.put(original, data, file.content_type or 'application/octet-stream')
        storage.put(oriented, out.getvalue())
        try:
            with db.begin_nested():
                p = Photo(batch_id=batch.id, sha256=digest, filename=(file.filename or 'photo')[:255],
                          original_key=original, oriented_key=oriented, width=image.width,
                          height=image.height, pipeline=s.pipeline)
                db.add(p); db.flush()
                db.add(Job(photo_id=p.id, stage='body_detection', pipeline=p.pipeline))
            result.append(photo_json(p))
        except IntegrityError:
            p = db.scalar(select(Photo).where(Photo.sha256 == digest))
            result.append({**photo_json(p), 'duplicate':True})
    db.commit()
    return {'batch_id':batch.id, 'photos':result}

@app.get('/api/photos/{photo_id}')
def detail(photo_id: str, db: DB):
    p = need(db, Photo, photo_id)
    heads = db.scalars(select(Observation).where(Observation.photo_id == p.id).order_by(Observation.index)).all()
    jobs = db.scalars(select(Job).where(Job.photo_id == p.id).order_by(Job.created_at)).all()
    return {**photo_json(p), 'heads':[head_json(db,o) for o in heads],
            'jobs':[dict(id=j.id,stage=j.stage,state=j.state,error=j.error,attempts=j.attempts) for j in jobs]}

@app.delete('/api/photos/{photo_id}')
def delete_photo(photo_id: str, db: DB):
    p = db.scalar(select(Photo).where(Photo.id == photo_id))
    if not p:
        raise HTTPException(404, 'Not found')
    # Workers lock a job before reading its photo. Use the same lock order so a
    # deletion waits for in-flight result handling without creating a deadlock.
    jobs = db.scalars(select(Job).where(Job.photo_id == p.id)
                      .order_by(Job.created_at, Job.id).with_for_update()).all()
    p = db.scalar(select(Photo).where(Photo.id == photo_id).with_for_update())
    if not p:
        raise HTTPException(404, 'Not found')
    heads = db.scalars(select(Observation).where(Observation.photo_id == p.id)).all()
    head_ids = [head.id for head in heads]
    job_ids = [job.id for job in jobs]
    object_keys = [p.original_key, p.oriented_key, *previews.keys_for(p.oriented_key)]
    for body in p.body_detections:
        if body.get('crop_key'):
            object_keys.extend([body['crop_key'], *previews.keys_for(body['crop_key'])])
    for head in heads:
        object_keys.extend([head.crop_key, *previews.keys_for(head.crop_key)])
    if head_ids:
        gallery = lock_gallery(db)
        gallery.revision += 1
        scrub_suggestion_candidates(db, lambda candidate: candidate.get('reference_id') in head_ids
                                    or (candidate.get('kind') == 'sighting'
                                        and candidate.get('id') in head_ids))
        db.execute(delete(Suggestion).where(Suggestion.observation_id.in_(head_ids)))
        db.execute(delete(Review).where(Review.observation_id.in_(head_ids)))
        db.execute(delete(CropReview).where(CropReview.observation_id.in_(head_ids)))
    if job_ids:
        db.execute(delete(Attempt).where(Attempt.job_id.in_(job_ids)))
    db.execute(delete(Job).where(Job.photo_id == p.id))
    db.execute(delete(Observation).where(Observation.photo_id == p.id))
    batch_id = p.batch_id
    db.delete(p)
    db.flush()
    if not db.scalar(select(Photo.id).where(Photo.batch_id == batch_id).limit(1)):
        batch = db.get(Batch, batch_id)
        if batch:
            db.delete(batch)
    db.commit()
    storage.delete_many(object_keys)
    return {'deleted':True, 'heads_deleted':len(head_ids)}

# Images travel through the restricted API tunnel. S3 never needs public access.
@app.get('/api/photos/{photo_id}/image')
def photo_image(photo_id: str, db: DB, variant: previews.Variant = 'original',
                if_none_match: Annotated[str | None, Header()] = None):
    return previews.response(need(db,Photo,photo_id).oriented_key, variant, if_none_match)
@app.get('/api/heads/{head_id}/image')
def head_image(head_id: str, db: DB, variant: previews.Variant = 'original',
               if_none_match: Annotated[str | None, Header()] = None):
    return previews.response(need(db,Observation,head_id).crop_key, variant, if_none_match)

@app.post('/api/photos/{photo_id}/recognize')
def recognize(photo_id: str, db: DB):
    p = db.scalar(select(Photo).where(Photo.id == photo_id).with_for_update())
    if not p: raise HTTPException(404)
    if p.detection_state != 'complete': raise HTTPException(409, 'Detection must finish first')
    heads = db.scalars(select(Observation).where(Observation.photo_id == p.id)).all()
    queued = queue_recognition(db, p, heads)
    db.commit()
    return {'queued':queued}

@app.post('/api/heads/{head_id}/crop-review')
def crop_review(head_id: str, body: CropReviewInput, db: DB):
    gallery = lock_gallery(db)
    o = db.scalar(select(Observation).where(Observation.id == head_id).with_for_update())
    if not o: raise HTTPException(404, 'Not found')
    if body.state == 'rejected' and o.review_state == 'confirmed':
        raise HTTPException(409, 'Remove the confirmed identity before rejecting this crop')
    if o.crop_review_state == body.state:
        return head_json(db, o)
    was_matchable = matchable(o)
    o.crop_review_state = body.state
    db.add(CropReview(observation_id=o.id, state=body.state))
    if body.state == 'rejected':
        scrub_suggestion_candidates(db, lambda candidate: candidate.get('reference_id') == o.id
                                    or (candidate.get('kind') == 'sighting'
                                        and candidate.get('id') == o.id))
        db.execute(delete(Suggestion).where(Suggestion.observation_id == o.id))
        o.embedding = None
        o.diagnostics = {}
        o.error = None
        o.recognition_state = 'not_requested'
    elif s.auto_recognize:
        queue_recognition(db, need(db, Photo, o.photo_id), [o])
    if was_matchable or matchable(o):
        gallery.revision += 1
    db.commit()
    return head_json(db, o)

@app.get('/api/heads/{head_id}/crop-history')
def crop_history(head_id: str, db: DB):
    need(db, Observation, head_id)
    return [dict(id=review.id, state=review.state, created_at=review.created_at) for review in
            db.scalars(select(CropReview).where(CropReview.observation_id == head_id)
                       .order_by(CropReview.created_at)).all()]

@app.post('/api/heads/{head_id}/review')
def review(head_id: str, body: ReviewInput, db: DB):
    gallery = lock_gallery(db)
    o = need(db,Observation,head_id)
    if o.crop_review_state != 'accepted':
        raise HTTPException(409, 'Accept the detected head crop before identity review')
    if body.state == 'confirmed':
        if not body.bear_id: raise HTTPException(400, 'Choose or create a bear')
        need(db,Bear,body.bear_id)
    elif body.bear_id: raise HTTPException(400, 'Only confirmed reviews assign a bear')
    o.review_state = body.state; o.bear_id = body.bear_id
    db.add(Review(observation_id=o.id, state=body.state, bear_id=body.bear_id))
    if s.auto_recognize and body.state == 'unresolved' and o.recognition_state in ('not_requested','failed'):
        queue_recognition(db, need(db, Photo, o.photo_id), [o])
    gallery.revision += 1
    db.commit()
    return head_json(db,o)

@app.get('/api/heads/{head_id}/history')
def history(head_id: str, db: DB):
    need(db,Observation,head_id)
    return [dict(id=r.id,state=r.state,bear_id=r.bear_id,created_at=r.created_at) for r in
            db.scalars(select(Review).where(Review.observation_id == head_id).order_by(Review.created_at)).all()]

def comparison_photo(db, observation):
    photo = need(db, Photo, observation.photo_id)
    return {'id':observation.id,
            'src':f'/api/heads/{observation.id}/image?variant=preview-v1',
            'label':photo.filename}

@app.get('/api/heads/{head_id}/matches')
def matches(head_id: str, db: DB):
    query = need(db, Observation, head_id)
    if query.crop_review_state != 'accepted' or query.embedding is None:
        raise HTTPException(409, 'Accepted crop recognition is required')
    result = []
    for candidate in candidates(db, query)[:MATCH_LIMIT]:
        reference = need(db, Observation, candidate['reference_id'])
        if candidate['kind'] == 'bear':
            gallery = db.scalars(select(Observation).where(
                Observation.bear_id == candidate['bear_id'],
                Observation.review_state == 'confirmed',
                Observation.crop_review_state == 'accepted',
                Observation.photo_id != query.photo_id)
                .order_by(Observation.created_at, Observation.id)).all()
            gallery = [reference] + [photo for photo in gallery if photo.id != reference.id]
            label = candidate['name'] or f"Unknown bear · {candidate['bear_id'][:8]}"
        else:
            gallery = [reference]
            label = f"Unidentified sighting · {candidate['id'][:8]}"
        result.append({'id':candidate['reference_id'], 'label':label, 'kind':candidate['kind'],
                       'similarity':candidate['cosine'],
                       'reference_id':candidate['reference_id'],
                       'bear_id':candidate['bear_id'],
                       'photos':[comparison_photo(db, photo) for photo in gallery]})
    return {'head':{'id':query.id, 'review_state':query.review_state,
                    'bear_id':query.bear_id, 'crop_url':f'/api/heads/{query.id}/image?variant=preview-v1'},
            'candidates':result}

def matchable(observation):
    return (observation.crop_review_state == 'accepted' and
            ((observation.review_state == 'confirmed' and observation.bear_id is not None) or
            (observation.review_state == 'unresolved' and observation.bear_id is None))
            )

@app.post('/api/heads/{head_id}/match')
def match(head_id: str, body: MatchInput, db: DB):
    gallery = lock_gallery(db)
    source = need(db, Observation, head_id)
    reference = need(db, Observation, body.reference_id)
    if (source.review_state != body.expected_review_state or
            source.bear_id != body.expected_bear_id):
        raise HTTPException(409, 'Sighting changed; refresh before confirming')
    if reference.bear_id != body.expected_reference_bear_id:
        raise HTTPException(409, 'Match changed; refresh before confirming')
    if source.id == reference.id or source.photo_id == reference.photo_id:
        raise HTTPException(409, 'A sighting cannot match the same original photo')
    if not matchable(source) or not matchable(reference):
        raise HTTPException(409, 'Sighting is not eligible for matching')
    if source.embedding_space != reference.embedding_space:
        raise HTTPException(409, 'Match uses an incompatible recognition pipeline')
    try:
        vector(source.embedding); vector(reference.embedding)
    except (ValueError, TypeError):
        raise HTTPException(409, 'Match has an incompatible embedding')

    reference_review = None
    if reference.review_state == 'confirmed':
        destination_id = reference.bear_id
        need(db, Bear, destination_id)
    else:
        destination = Bear(name=None); db.add(destination); db.flush()
        destination_id = destination.id
        reference.review_state = 'confirmed'; reference.bear_id = destination_id
        reference_review = Review(observation_id=reference.id, state='confirmed', bear_id=destination_id)

    source.review_state = 'confirmed'; source.bear_id = destination_id
    source_review = Review(observation_id=source.id, state='confirmed', bear_id=destination_id)
    db.add(source_review)
    if reference_review is not None:
        db.add(reference_review)
    gallery.revision += 1
    db.flush()
    undo = {'head_review_id':source_review.id,
            'reference_review_id':reference_review.id if reference_review else None}
    db.commit()
    return {'head':head_json(db, source), 'undo':undo}

def review_history(db, observation_id):
    return db.scalars(select(Review).where(Review.observation_id == observation_id)
        .order_by(Review.created_at.desc(), Review.id.desc())).all()

def prior_review(history):
    return (history[1].state, history[1].bear_id) if len(history) > 1 else ('unresolved', None)

@app.post('/api/heads/{head_id}/undo-match')
def undo_match(head_id: str, body: UndoMatchInput, db: DB):
    gallery = lock_gallery(db)
    source = need(db, Observation, head_id)
    source_event = db.get(Review, body.head_review_id)
    source_history = review_history(db, source.id)
    if (source_event is None or source_event.observation_id != source.id or
            not source_history or source_history[0].id != source_event.id or
            source_event.state != 'confirmed' or source_event.bear_id is None or
            source.review_state != source_event.state or source.bear_id != source_event.bear_id):
        raise HTTPException(409, 'Match can no longer be undone')

    reference = None
    reference_history = []
    if body.reference_review_id is not None:
        reference_event = db.get(Review, body.reference_review_id)
        if reference_event is None:
            raise HTTPException(409, 'Match can no longer be undone')
        reference = need(db, Observation, reference_event.observation_id)
        reference_history = review_history(db, reference.id)
        if (reference.id == source.id or not reference_history or
                reference_history[0].id != reference_event.id or
                reference_event.state != 'confirmed' or
                reference_event.bear_id != source_event.bear_id or
                reference.review_state != reference_event.state or
                reference.bear_id != reference_event.bear_id):
            raise HTTPException(409, 'Match can no longer be undone')

    source.review_state, source.bear_id = prior_review(source_history)
    db.add(Review(observation_id=source.id, state=source.review_state, bear_id=source.bear_id))
    if reference is not None:
        reference.review_state, reference.bear_id = prior_review(reference_history)
        db.add(Review(observation_id=reference.id, state=reference.review_state,
                      bear_id=reference.bear_id))
    gallery.revision += 1
    db.commit()
    return head_json(db, source)

@app.post('/api/heads/{head_id}/refresh')
def refresh(head_id: str, db: DB):
    gallery = lock_gallery(db); o = need(db,Observation,head_id)
    if o.crop_review_state != 'accepted' or o.embedding is None:
        raise HTTPException(409, 'Accepted crop recognition is required')
    snapshot(db,o,gallery); db.commit()
    return head_json(db,o)

@app.get('/api/bears')
def bears(db: DB):
    thumbnails = {}
    photo_ids = {}
    for oid, bid, photo_id, state, crop_state in db.execute(select(
            Observation.id, Observation.bear_id, Observation.photo_id,
            Observation.review_state, Observation.crop_review_state).where(
            Observation.bear_id.is_not(None))
            .order_by(Observation.created_at, Observation.id)):
        photo_ids.setdefault(bid, set()).add(photo_id)
        if state == 'confirmed' and crop_state == 'accepted':
            thumbnails.setdefault(bid, f'/api/heads/{oid}/image?variant=thumbnail-v1')
    return [dict(id=b.id,name=b.name,thumbnail_url=thumbnails.get(b.id),
                 photo_count=len(photo_ids.get(b.id, set())))
            for b in db.scalars(select(Bear).order_by(Bear.created_at)).all()]
@app.post('/api/bears')
def create_bear(body: BearInput, db: DB):
    b = Bear(name=(body.name or '').strip() or None); db.add(b); db.commit()
    return dict(id=b.id,name=b.name)
@app.patch('/api/bears/{bear_id}')
def rename(bear_id: str, body: BearInput, db: DB):
    b = need(db,Bear,bear_id); b.name = (body.name or '').strip() or None; db.commit()
    return dict(id=b.id,name=b.name)
@app.delete('/api/bears/{bear_id}')
def delete_bear(bear_id: str, db: DB):
    gallery = lock_gallery(db)
    b = db.scalar(select(Bear).where(Bear.id == bear_id).with_for_update())
    if not b:
        raise HTTPException(404, 'Not found')
    assigned = db.scalars(select(Observation).where(Observation.bear_id == b.id)).all()
    if assigned:
        photo_count = len({observation.photo_id for observation in assigned})
        raise HTTPException(409, f'Reassign or remove this bear from its {photo_count} associated photo'
                                f'{"s" if photo_count != 1 else ""} before deleting it')
    db.execute(delete(Review).where(Review.bear_id == b.id))
    scrub_suggestion_candidates(db, lambda candidate: candidate.get('bear_id') == b.id
                                or (candidate.get('kind') == 'bear'
                                    and candidate.get('id') == b.id))
    db.delete(b)
    gallery.revision += 1
    db.commit()
    return {'deleted':True}
@app.get('/api/bears/{bear_id}/references')
def references(bear_id: str, db: DB):
    need(db,Bear,bear_id)
    return [head_json(db,o) for o in db.scalars(select(Observation).where(
        Observation.bear_id == bear_id, Observation.crop_review_state == 'accepted',
        Observation.review_state == 'confirmed', Observation.embedding.is_not(None))).all()]

@app.post('/api/jobs/{job_id}/retry')
def retry(job_id: str, db: DB):
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if not job: raise HTTPException(404)
    if job.state != 'failed': raise HTTPException(409, 'Only failed jobs can retry')
    if job.stage == 'recognition':
        raise HTTPException(409, 'Use Retry recognition for failed eligible heads')
    photo = need(db,Photo,job.photo_id)
    if job.pipeline != s.pipeline:
        if db.scalar(select(Observation.id).where(Observation.photo_id == photo.id).limit(1)):
            raise HTTPException(409, 'Existing observations cannot move to another pipeline')
        photo.pipeline = s.pipeline
    # A new bounded job preserves prior attempts and uses the deployed pipeline.
    retry_stage = 'body_detection' if job.stage == 'detection' else job.stage
    db.add(Job(photo_id=job.photo_id,stage=retry_stage,pipeline=photo.pipeline))
    photo.detection_state = 'queued'
    job.state = 'superseded'; db.commit()
    return {'queued':True}

def fail_job(db, job, error):
    job.error = error[:2000]
    attempt = db.scalar(select(Attempt).where(Attempt.token == job.token))
    if attempt: attempt.state = 'failed'; attempt.error = job.error
    job.state = 'failed' if job.attempts >= s.max_attempts else 'queued'
    if job.stage in ('body_detection','head_detection'):
        need(db,Photo,job.photo_id).detection_state = job.state
    else:
        for oid in job.observation_ids:
            o = need(db,Observation,oid)
            if o.crop_review_state == 'accepted' and o.recognition_state != 'complete':
                o.recognition_state = job.state; o.error = job.error

def assert_lease(job, token):
    if job.token != token or job.state != 'running' or job.lease_until <= now():
        raise HTTPException(409, 'Stale or expired attempt')

@app.post('/internal/jobs/claim', dependencies=[Depends(require_worker)])
def claim(body: Claim, db: DB):
    if body.pipeline != s.pipeline: raise HTTPException(409, 'Pipeline mismatch')
    # Reap expired leases under the same row locks used for claims/results.
    expired = db.scalars(select(Job).where(Job.state == 'running', Job.lease_until < now()).with_for_update(skip_locked=True)).all()
    for job in expired: fail_job(db,job,'Worker lease expired')
    job = db.scalar(select(Job).where(Job.state == 'queued', Job.stage == body.stage,
                    Job.pipeline == body.pipeline).order_by(Job.created_at).with_for_update(skip_locked=True).limit(1))
    if not job: db.commit(); return None
    job.attempts += 1; job.token = uid(); job.state = 'running'; job.started_at = now()
    job.lease_until = now() + timedelta(seconds=s.lease_seconds)
    db.add(Attempt(job_id=job.id,token=job.token,org_id=job.org_id))
    p = need(db,Photo,job.photo_id)
    if job.stage in ('body_detection','head_detection'): p.detection_state = 'running'
    bodies = []
    if job.stage == 'head_detection':
        bodies = [{**body, 'url':storage.signed(body['crop_key'])}
                  for body in p.body_detections]
    heads = []
    for oid in job.observation_ids:
        o = need(db,Observation,oid)
        if (o.recognition_state == 'complete' or o.crop_review_state != 'accepted'
                or o.review_state in ('ignored','unusable')): continue
        o.recognition_state = 'running'
        heads.append({'observation_id':o.id,'crop_key':o.crop_key,'url':storage.signed(o.crop_key)})
    payload = dict(job_id=job.id,token=job.token,stage=job.stage,pipeline=job.pipeline,
                   attempt=job.attempts,photo_id=p.id,filename=p.filename,
                   original_key=p.original_key,oriented_key=p.oriented_key,
                   url=storage.signed(p.oriented_key),width=p.width,height=p.height,
                   bodies=bodies,heads=heads)
    db.commit(); return payload

@app.post('/internal/jobs/{job_id}/heartbeat', dependencies=[Depends(require_worker)])
def heartbeat(job_id: str, body: Lease, db: DB):
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update());
    if not job: raise HTTPException(404)
    db.info['org_id'] = job.org_id
    assert_lease(job,body.token)
    if (now() - job.started_at).total_seconds() >= s.job_timeout_seconds:
        fail_job(db,job,'Job time limit exceeded'); db.commit(); raise HTTPException(409,'Job time limit exceeded')
    job.lease_until = min(now() + timedelta(seconds=s.lease_seconds), job.started_at + timedelta(seconds=s.job_timeout_seconds))
    db.commit(); return {'ok':True}

@app.post('/internal/jobs/{job_id}/result', dependencies=[Depends(require_worker)])
def result(job_id: str, body: Result, db: DB):
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if not job: raise HTTPException(404)
    if job.token == body.token and job.state == 'complete': return {'ok':True,'duplicate':True}
    db.info['org_id'] = job.org_id
    assert_lease(job,body.token)
    if body.pipeline != job.pipeline or body.provenance.get('mode') != ('mock' if s.pipeline.startswith('mock') else 'real'):
        raise HTTPException(409,'Result provenance mismatch')
    if body.error:
        fail_job(db,job,body.error); db.commit(); return {'ok':True}
    p = need(db,Photo,job.photo_id)
    if job.stage == 'body_detection':
        detection = body.body_detection
        if not detection or (detection.width, detection.height) != (p.width, p.height):
            raise HTTPException(422, 'Oriented dimensions mismatch')
        image = Image.open(io.BytesIO(storage.get(p.oriented_key))).convert('RGB')
        bodies = []
        for item in detection.detections:
            try:
                metadata = body_crop(item, p.width, p.height)
            except ValueError as error:
                raise HTTPException(422, str(error))
            if metadata is None:
                continue
            index = len(bodies)
            key = f'body-crops/{p.id}/{index}.jpg'
            storage.put(key, encode_jpeg_crop(image, metadata['crop_box']), 'image/jpeg')
            bodies.append({**metadata, 'index':index, 'crop_key':key})
        p.body_detections = bodies
        p.provenance = {'body':body.provenance}
        if bodies:
            db.add(Job(photo_id=p.id, stage='head_detection', pipeline=job.pipeline,
                       org_id=job.org_id))
            p.detection_state = 'queued'
        else:
            p.detection_state = 'complete'
    elif job.stage == 'head_detection':
        expected = {item['index']:item for item in p.body_detections}
        received = [item.body_index for item in body.head_detections]
        if len(received) != len(set(received)) or set(received) != set(expected):
            raise HTTPException(422, 'Unexpected, duplicate, or missing body results')
        accepted = []
        body_images = {}
        for result_item in body.head_detections:
            body_metadata = expected[result_item.body_index]
            if (result_item.width, result_item.height) != (
                    body_metadata['width'], body_metadata['height']):
                raise HTTPException(422, 'Body crop dimensions mismatch')
            body_image = Image.open(io.BytesIO(storage.get(body_metadata['crop_key']))).convert('RGB')
            body_images[result_item.body_index] = body_image
            for box in result_item.boxes:
                try:
                    metadata = head_crop(box, body_metadata)
                except ValueError as error:
                    raise HTTPException(422, str(error))
                if metadata is not None:
                    accepted.append((result_item.body_index, metadata))
        for index, (body_index, metadata) in enumerate(accepted):
            key = f'crops/{p.id}/{index}.jpg'
            storage.put(key, encode_jpeg_crop(body_images[body_index], metadata['local_box']),
                        'image/jpeg')
            db.add(Observation(
                photo_id=p.id, index=index, body_index=body_index,
                detector_score=metadata['score'], box=metadata['box'], crop_key=key,
                pipeline=job.pipeline, embedding_space=embedding_space(job.pipeline),
                crop_review_state='pending', recognition_state='not_requested',
                org_id=job.org_id))
        p.detections = [{'body_index':item.body_index, 'boxes':item.boxes}
                        for item in body.head_detections]
        p.provenance = {**p.provenance, 'head':body.provenance}
        p.detection_state = 'complete'
    else:
        gallery = lock_gallery(db)
        ids = [h.observation_id for h in body.heads]
        if len(ids) != len(set(ids)) or not set(ids).issubset(set(job.observation_ids)):
            raise HTTPException(422,'Unexpected or duplicate head results')
        by_id = {h.observation_id:h for h in body.heads}
        for oid in job.observation_ids:
            o = need(db,Observation,oid)
            if o.recognition_state == 'complete': continue
            if o.crop_review_state != 'accepted' or o.review_state in ('ignored','unusable'):
                o.recognition_state = 'not_requested'; continue
            h = by_id.get(oid)
            try:
                if not h or h.error: raise ValueError(h.error if h else 'Missing head result')
                vector(h.embedding)
                # The embedding belongs to the model that produced it; retain
                # the photo's original detection provenance and completed heads.
                o.pipeline = job.pipeline
                o.embedding_space = embedding_space(job.pipeline)
                o.embedding = h.embedding; o.diagnostics = {**h.diagnostics,'provenance':body.provenance}
                o.recognition_state = 'complete'; o.error = None
                if matchable(o): gallery.revision += 1
                snapshot(db,o,gallery)
            except (ValueError,TypeError) as e:
                o.recognition_state = 'failed'; o.error = str(e)[:2000]
    job.state = 'complete'
    attempt = db.scalar(select(Attempt).where(Attempt.token == job.token)); attempt.state = 'complete'
    db.commit(); return {'ok':True}

from .auth import install as install_auth
install_auth(app)
from .member_admin import install as install_member_admin
install_member_admin(app, s)
