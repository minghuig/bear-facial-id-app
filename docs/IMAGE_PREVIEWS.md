# Portal image delivery

Photo API responses expose `thumbnail_url` (160 px maximum edge) and
`image_url` (1280 px maximum edge). Head `crop_url` uses the 1280 px preview;
candidate rows request the thumbnail. Both variants use JPEG quality 82,
preserve aspect ratio, and never upscale. Photo dimensions and detection
coordinates remain in original pixels; the UI overlays use percentages.

The original `/api/photos/{id}/image` and `/api/heads/{id}/image` routes without
a variant still return the full PNG. Workers continue using original storage
keys. Uploaded files and inference inputs are not changed.

Variants are generated on their first request and persisted beneath `previews/`
in the same private bucket. Existing uploads therefore work without re-uploading
or database migrations. The first request fetches and decodes the original on
the server; subsequent requests read only the derivative. Simultaneous cold
requests can duplicate generation but write the same derivative. Browser image
responses use `Cache-Control: private, max-age=86400` and ETags; matching
conditional requests return 304 after validating the record, without S3 reads.

The version in the variant URL and derivative key must change if encoding or
dimensions change. This assumes published original photo and completed crop
objects are immutable, as they are in the current workflow. Bucket access stays
private and image responses still traverse the authenticated API tunnel.

## Validation

Run the backend suite using the disposable PostgreSQL setup in `tests/README.md`,
including `tests/test_image_previews.py`, then run `npm run build` in `frontend`.
Tests cover aspect ratio, size bounds, no upscaling, original-byte preservation,
reuse of derivatives, conditional caching, invalid variants, missing records,
and storage-error propagation.

Measured locally on the previously diagnosed 5184 × 3888 photo:

| Asset | Bytes | Dimensions |
| --- | ---: | --- |
| Oriented PNG | 24,764,063 | 5184 × 3888 |
| Thumbnail | 5,561 | 160 × 120 |
| Preview | 226,222 | 1280 × 960 |

Generation took about 1.1 and 1.5 seconds respectively on the local test host.
These are payload and local generation measurements, not post-deployment AWS
latency measurements. After deployment, verify cold/warm loads and browser
caching through the portal, and check head overlays against the photo.
