import hashlib
import hmac
import io
import math
import os
from datetime import timedelta
from typing import Annotated
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select, or_, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .config import settings
from .db import session
from .models import Batch, Photo, Observation, Bear, Review, Gallery, Suggestion, Job, Attempt, now, uid
from .contracts import Claim, Lease, Result, ReviewInput, BearInput
from . import storage, previews
from .retrieval import snapshot, vector

s = settings()
app = FastAPI(title='Only Bears')
app.add_middleware(CORSMiddleware, allow_origins=[s.cors_origin], allow_methods=['GET','POST','PATCH'], allow_headers=['Content-Type'])
@app.middleware('http')
async def restrict_browser_origin(request: Request, call_next):
    origin = request.headers.get('origin')
    if request.method not in ('GET','HEAD','OPTIONS') and origin and origin != s.cors_origin:
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

def lock_gallery(db):
    return db.scalar(select(Gallery).where(Gallery.id == 1).with_for_update())

def photo_json(p):
    return dict(id=p.id, filename=p.filename, width=p.width, height=p.height,
                detection_state=p.detection_state, pipeline=p.pipeline, created_at=p.created_at,
                image_url=f'/api/photos/{p.id}/image?variant=preview-v1',
                thumbnail_url=f'/api/photos/{p.id}/image?variant=thumbnail-v1')

def head_json(db, o):
    suggestions = db.scalars(select(Suggestion).where(Suggestion.observation_id == o.id).order_by(Suggestion.created_at.desc())).all()
    return dict(id=o.id, photo_id=o.photo_id, index=o.index, box=o.box,
                crop_url=f'/api/heads/{o.id}/image?variant=preview-v1', recognition_state=o.recognition_state,
                review_state=o.review_state, bear_id=o.bear_id, error=o.error,
                suggestions=[dict(id=x.id, pipeline=x.pipeline, gallery_revision=x.gallery_revision,
                                  created_at=x.created_at, candidates=x.candidates) for x in suggestions])

@app.get('/health')
def health(db: DB):
    db.execute(text('SELECT 1'))
    return {'status':'ok', 'pipeline':s.pipeline, 'environment':s.environment, 'commit':os.getenv('RELEASE_COMMIT','development')}

@app.get('/api/photos')
def photos(db: DB):
    return [photo_json(p) for p in db.scalars(select(Photo).order_by(Photo.created_at.desc())).all()]

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
        original = f'photos/{digest}/original'
        oriented = f'photos/{digest}/oriented.png'
        out = io.BytesIO(); image.save(out, format='PNG')
        storage.put(original, data, file.content_type or 'application/octet-stream')
        storage.put(oriented, out.getvalue())
        try:
            with db.begin_nested():
                p = Photo(batch_id=batch.id, sha256=digest, filename=(file.filename or 'photo')[:255],
                          original_key=original, oriented_key=oriented, width=image.width,
                          height=image.height, pipeline=s.pipeline)
                db.add(p); db.flush()
                db.add(Job(photo_id=p.id, stage='detection', pipeline=p.pipeline))
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
    heads = db.scalars(select(Observation).where(Observation.photo_id == p.id,
        Observation.review_state.not_in(['ignored','unusable']),
        Observation.recognition_state.in_(['not_requested','failed']))).all()
    if not heads: return {'queued':0}
    job = Job(photo_id=p.id, stage='recognition', pipeline=p.pipeline, observation_ids=[o.id for o in heads])
    db.add(job)
    for o in heads: o.recognition_state = 'queued'; o.error = None
    db.commit()
    return {'queued':len(heads)}

@app.post('/api/heads/{head_id}/review')
def review(head_id: str, body: ReviewInput, db: DB):
    gallery = lock_gallery(db)
    o = need(db,Observation,head_id)
    if body.state == 'confirmed':
        if not body.bear_id: raise HTTPException(400, 'Choose or create a bear')
        need(db,Bear,body.bear_id)
    elif body.bear_id: raise HTTPException(400, 'Only confirmed reviews assign a bear')
    o.review_state = body.state; o.bear_id = body.bear_id
    db.add(Review(observation_id=o.id, state=body.state, bear_id=body.bear_id))
    gallery.revision += 1
    db.commit()
    return head_json(db,o)

@app.get('/api/heads/{head_id}/history')
def history(head_id: str, db: DB):
    need(db,Observation,head_id)
    return [dict(id=r.id,state=r.state,bear_id=r.bear_id,created_at=r.created_at) for r in
            db.scalars(select(Review).where(Review.observation_id == head_id).order_by(Review.created_at)).all()]

@app.post('/api/heads/{head_id}/refresh')
def refresh(head_id: str, db: DB):
    gallery = lock_gallery(db); o = need(db,Observation,head_id)
    if o.embedding is None: raise HTTPException(409, 'Recognition required')
    snapshot(db,o,gallery); db.commit()
    return head_json(db,o)

@app.get('/api/bears')
def bears(db: DB):
    return [dict(id=b.id,name=b.name) for b in db.scalars(select(Bear).order_by(Bear.created_at)).all()]
@app.post('/api/bears')
def create_bear(body: BearInput, db: DB):
    b = Bear(name=(body.name or '').strip() or None); db.add(b); db.commit()
    return dict(id=b.id,name=b.name)
@app.patch('/api/bears/{bear_id}')
def rename(bear_id: str, body: BearInput, db: DB):
    b = need(db,Bear,bear_id); b.name = (body.name or '').strip() or None; db.commit()
    return dict(id=b.id,name=b.name)
@app.get('/api/bears/{bear_id}/references')
def references(bear_id: str, db: DB):
    need(db,Bear,bear_id)
    return [head_json(db,o) for o in db.scalars(select(Observation).where(
        Observation.bear_id == bear_id, Observation.review_state == 'confirmed', Observation.embedding.is_not(None))).all()]

@app.post('/api/jobs/{job_id}/retry')
def retry(job_id: str, db: DB):
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if not job: raise HTTPException(404)
    if job.state != 'failed': raise HTTPException(409, 'Only failed jobs can retry')
    if job.stage == 'recognition':
        raise HTTPException(409, 'Use Run recognition to retry failed eligible heads')
    photo = need(db,Photo,job.photo_id)
    if job.pipeline != s.pipeline:
        if db.scalar(select(Observation.id).where(Observation.photo_id == photo.id).limit(1)):
            raise HTTPException(409, 'Existing observations cannot move to another pipeline')
        photo.pipeline = s.pipeline
    # A new bounded job preserves prior attempts and uses the deployed pipeline.
    db.add(Job(photo_id=job.photo_id,stage=job.stage,pipeline=photo.pipeline))
    photo.detection_state = 'queued'
    job.state = 'superseded'; db.commit()
    return {'queued':True}

def fail_job(db, job, error):
    job.error = error[:2000]
    attempt = db.scalar(select(Attempt).where(Attempt.token == job.token))
    if attempt: attempt.state = 'failed'; attempt.error = job.error
    job.state = 'failed' if job.attempts >= s.max_attempts else 'queued'
    if job.stage == 'detection': need(db,Photo,job.photo_id).detection_state = job.state
    else:
        for oid in job.observation_ids:
            o = need(db,Observation,oid)
            if o.recognition_state != 'complete': o.recognition_state = job.state; o.error = job.error

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
    db.add(Attempt(job_id=job.id,token=job.token))
    p = need(db,Photo,job.photo_id)
    if job.stage == 'detection': p.detection_state = 'running'
    heads = []
    for oid in job.observation_ids:
        o = need(db,Observation,oid)
        if o.recognition_state == 'complete' or o.review_state in ('ignored','unusable'): continue
        o.recognition_state = 'running'
        heads.append({'observation_id':o.id,'crop_key':o.crop_key,'url':storage.signed(o.crop_key)})
    payload = dict(job_id=job.id,token=job.token,stage=job.stage,pipeline=job.pipeline,
                   attempt=job.attempts,photo_id=p.id,filename=p.filename,
                   original_key=p.original_key,oriented_key=p.oriented_key,
                   url=storage.signed(p.oriented_key),width=p.width,height=p.height,heads=heads)
    db.commit(); return payload

@app.post('/internal/jobs/{job_id}/heartbeat', dependencies=[Depends(require_worker)])
def heartbeat(job_id: str, body: Lease, db: DB):
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update());
    if not job: raise HTTPException(404)
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
    assert_lease(job,body.token)
    if body.pipeline != job.pipeline or body.provenance.get('mode') != ('mock' if s.pipeline.startswith('mock') else 'real'):
        raise HTTPException(409,'Result provenance mismatch')
    if body.error:
        fail_job(db,job,body.error); db.commit(); return {'ok':True}
    p = need(db,Photo,job.photo_id)
    if job.stage == 'detection':
        d = body.detection
        if not d or (d.width,d.height) != (p.width,p.height): raise HTTPException(422,'Oriented dimensions mismatch')
        accepted = []
        for box in d.boxes:
            if len(box) != 5 or not all(math.isfinite(x) for x in box) or not 0 <= box[4] <= 1:
                raise HTTPException(422,'Invalid detector box')
            if box[4] < .5: continue
            x1,y1,x2,y2 = max(0,math.floor(box[0])),max(0,math.floor(box[1])),min(p.width,math.ceil(box[2])),min(p.height,math.ceil(box[3]))
            if x2 > x1 and y2 > y1: accepted.append([x1,y1,x2,y2])
        image = Image.open(io.BytesIO(storage.get(p.oriented_key)))
        for index, box in enumerate(accepted):
            key = f'crops/{p.id}/{index}.png'
            out = io.BytesIO(); image.crop(box).save(out,format='PNG'); storage.put(key,out.getvalue())
            db.add(Observation(photo_id=p.id,index=index,box=box,crop_key=key,pipeline=p.pipeline))
        p.detections = d.boxes; p.provenance = body.provenance; p.detection_state = 'complete'
        # Intentionally no recognition job: this persisted pause is the product boundary.
    else:
        gallery = lock_gallery(db)
        ids = [h.observation_id for h in body.heads]
        if len(ids) != len(set(ids)) or not set(ids).issubset(set(job.observation_ids)):
            raise HTTPException(422,'Unexpected or duplicate head results')
        by_id = {h.observation_id:h for h in body.heads}
        for oid in job.observation_ids:
            o = need(db,Observation,oid)
            if o.recognition_state == 'complete': continue
            if o.review_state in ('ignored','unusable'):
                o.recognition_state = 'not_requested'; continue
            h = by_id.get(oid)
            try:
                if not h or h.error: raise ValueError(h.error if h else 'Missing head result')
                vector(h.embedding)
                o.embedding = h.embedding; o.diagnostics = {**h.diagnostics,'provenance':body.provenance}
                o.recognition_state = 'complete'; o.error = None
                if o.review_state == 'confirmed': gallery.revision += 1
                snapshot(db,o,gallery)
            except (ValueError,TypeError) as e:
                o.recognition_state = 'failed'; o.error = str(e)[:2000]
    job.state = 'complete'
    attempt = db.scalar(select(Attempt).where(Attempt.token == job.token)); attempt.state = 'complete'
    db.commit(); return {'ok':True}
