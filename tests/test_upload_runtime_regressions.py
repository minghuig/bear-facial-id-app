import io
from PIL import Image
from sqlalchemy import select
from app import main
from app.models import Job, Photo, Observation


def test_jpeg_with_mpo_metadata_accepts_primary_frame(api):
    client, factory, objects = api
    stream = io.BytesIO()
    Image.new('RGB', (40, 30), 'brown').save(
        stream, 'MPO', save_all=True, append_images=[Image.new('RGB', (40, 30), 'blue')])
    data = stream.getvalue()
    assert Image.open(io.BytesIO(data)).format == 'MPO'
    response = client.post('/api/photos', files={'files': ('camera.jpg', data, 'image/jpeg')})
    row = response.json()['photos'][0]
    assert 'error' not in row, row
    assert (row['width'], row['height']) == (40, 30)
    assert data in objects.values()
    with factory() as db:
        assert db.scalar(select(Job)).photo_id == row['id']


def failed_photo(api):
    client, factory, _ = api
    stream = io.BytesIO()
    Image.new('RGB', (40, 30), 'brown').save(stream, 'JPEG')
    row = client.post('/api/photos', files={'files': ('bear.jpg', stream.getvalue(), 'image/jpeg')}).json()['photos'][0]
    with factory.begin() as db:
        photo = db.get(Photo, row['id'])
        job = db.scalar(select(Job).where(Job.photo_id == photo.id))
        photo.pipeline = job.pipeline = 'retired-pipeline'
        photo.detection_state = job.state = 'failed'
        return photo.id, job.id


def test_failed_detection_retry_uses_current_pipeline_preserving_old_job(api):
    client, factory, _ = api
    photo_id, job_id = failed_photo(api)
    assert client.post(f'/api/jobs/{job_id}/retry').status_code == 200
    with factory() as db:
        old = db.get(Job, job_id)
        new = db.scalar(select(Job).where(Job.id != job_id))
        assert old.state == 'superseded' and old.pipeline == 'retired-pipeline'
        assert new.pipeline == db.get(Photo, photo_id).pipeline == main.s.pipeline


def test_retry_cannot_move_existing_observations_between_pipelines(api):
    client, factory, _ = api
    photo_id, job_id = failed_photo(api)
    with factory.begin() as db:
        db.add(Observation(photo_id=photo_id, index=0, box=[0,0,10,10],
                           crop_key='saved-crop', pipeline='retired-pipeline'))
    assert client.post(f'/api/jobs/{job_id}/retry').status_code == 409
