import io

from PIL import Image
import pytest
from botocore.exceptions import ClientError

from app import storage
from app.models import Photo, Observation


def uploaded(api):
    client, factory, objects = api
    out = io.BytesIO()
    Image.new('RGB', (2400, 1600), 'brown').save(out, 'JPEG')
    photo = client.post('/api/photos', files={'files': ('bear.jpg', out.getvalue(), 'image/jpeg')}).json()['photos'][0]
    return photo


def test_photo_variants_preserve_original_and_cache_existing_upload(api, monkeypatch):
    client, factory, objects = api
    photo = uploaded(api)
    original = client.get(f"/api/photos/{photo['id']}/image")
    assert Image.open(io.BytesIO(original.content)).size == (2400, 1600)
    for field, limit in [('thumbnail_url', 160), ('image_url', 1280)]:
        response = client.get(photo[field])
        assert response.headers['content-type'] == 'image/jpeg'
        image = Image.open(io.BytesIO(response.content))
        assert max(image.size) <= limit
        assert abs(image.width / image.height - 1.5) < .01
        assert response.headers['cache-control'].startswith('private,')
        etag = response.headers['etag']
        # A subsequent request must use the stored derivative, not fetch/decode the original.
        with factory() as db:
            original_key = db.get(Photo, photo['id']).oriented_key
        get = storage.get
        def cached_get(key):
            assert key != original_key
            return get(key)
        with monkeypatch.context() as patch:
            patch.setattr(storage, 'get', cached_get)
            assert client.get(photo[field]).content == response.content
            patch.setattr(storage, 'get', lambda key: (_ for _ in ()).throw(AssertionError('304 read storage')))
            patch.setattr(storage, 'get_optional', lambda key: (_ for _ in ()).throw(AssertionError('304 read derivative')))
            cached = client.get(photo[field], headers={'If-None-Match': f'"other", W/{etag}'})
            assert cached.status_code == 304 and cached.content == b''
        assert client.get(photo[field], headers={'If-None-Match': '"stale"'}).status_code == 200
    assert client.get(f"/api/photos/{photo['id']}/image").content == original.content


def test_head_preview_small_source_and_invalid_variant(api):
    client, factory, objects = api
    photo = uploaded(api)
    out = io.BytesIO()
    Image.new('RGB', (90, 60), 'brown').save(out, 'PNG')
    objects['head-original'] = out.getvalue()
    with factory.begin() as db:
        p = db.get(Photo, photo['id'])
        head = Observation(photo_id=p.id, index=0, box=[0, 0, 90, 60], crop_key='head-original', pipeline=p.pipeline)
        db.add(head)
        db.flush()
        head_id = head.id
    detail = client.get('/api/photos/' + photo['id']).json()
    response = client.get(detail['heads'][0]['crop_url'])
    assert response.headers['content-type'] == 'image/jpeg'
    assert Image.open(io.BytesIO(response.content)).size == (90, 60)
    assert client.get(f'/api/heads/{head_id}/image').content == out.getvalue()
    assert client.get(f'/api/heads/{head_id}/image?variant=arbitrary').status_code == 422
    assert client.get('/api/photos/missing/image?variant=preview-v1').status_code == 404


@pytest.mark.parametrize('code', ['NoSuchKey', '404', 'AccessDenied', 'SlowDown'])
def test_derivative_lookup_only_treats_missing_objects_as_cache_misses(monkeypatch, code):
    error = ClientError({'Error': {'Code': code}}, 'GetObject')
    def fail(key):
        raise error
    monkeypatch.setattr(storage, 'get', fail)
    if code in ('NoSuchKey', '404'):
        assert storage.get_optional('missing-preview') is None
    else:
        with pytest.raises(ClientError) as caught:
            storage.get_optional('preview')
        assert caught.value is error
