"""Private, persisted display derivatives; inference always uses original assets."""
import hashlib
import io
from typing import Literal

from fastapi.responses import Response
from PIL import Image

from . import storage

# Version URLs and storage keys together when changing encoding or dimensions.
Variant = Literal['original', 'thumbnail-v1', 'preview-v1']
SIZES = {'thumbnail-v1': 160, 'preview-v1': 1280}


def jpeg(data: bytes, limit: int) -> bytes:
    with Image.open(io.BytesIO(data)) as image:
        image.thumbnail((limit, limit), Image.Resampling.LANCZOS)
        output = io.BytesIO()
        image.convert('RGB').save(output, 'JPEG', quality=82, optimize=True)
        return output.getvalue()


def response(key: str, variant: Variant, if_none_match: str | None) -> Response:
    # Published sources are immutable (photo digest or completed detection crop).
    digest = hashlib.sha256(f'{key}:{variant}'.encode()).hexdigest()
    etag = f'"{digest}"'
    headers = {'Cache-Control': 'private, max-age=86400', 'ETag': etag}
    if if_none_match and any(tag.strip().removeprefix('W/') in (etag, '*')
                             for tag in if_none_match.split(',')):
        return Response(status_code=304, headers=headers)
    if variant == 'original':
        return Response(storage.get(key), media_type='image/png', headers=headers)
    derived_key = f'previews/{digest}/{variant}.jpg'
    data = storage.get_optional(derived_key)
    if data is None:
        data = jpeg(storage.get(key), SIZES[variant])
        storage.put(derived_key, data, 'image/jpeg')
    return Response(data, media_type='image/jpeg', headers=headers)
