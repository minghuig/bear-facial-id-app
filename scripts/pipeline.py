#!/usr/bin/env python3
"""Content-derived namespace: changing adapters, source or preprocessing isolates galleries."""
import hashlib
from pathlib import Path
root = Path(__file__).resolve().parents[1]
h = hashlib.sha256(b'body-md4.1-thr>.90;original-3pct-edge-padding;head-on-body-thr=.5;manual-crop-curation;RGB224;imagenet;flip-sum-l2;512;stage-v2')
paths = [root/'workers'/n for n in ['trusted.py','body_detector.py','detector.py','recognition.py',
                                    'run_stage.py','Dockerfile.body-detector','Dockerfile.detector',
                                    'Dockerfile.recognition']]
paths.append(root/'backend/app/detection.py')
paths += sorted((root/'workers/vendor').rglob('*.py'))
for path in paths:
    h.update(path.relative_to(root).as_posix().encode()); h.update(path.read_bytes())
print('real-v1-'+h.hexdigest()[:16])
