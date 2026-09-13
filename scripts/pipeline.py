#!/usr/bin/env python3
"""Content-derived namespace: changing adapters, source or preprocessing isolates galleries."""
import hashlib
from pathlib import Path
root = Path(__file__).resolve().parents[1]
h = hashlib.sha256(b'head-original-exif;thr=.5;floorceil-no-margin;RGB224;imagenet;flip-sum-l2;512;stage-v1')
paths = [root/'workers'/n for n in ['trusted.py','detector.py','recognition.py','run_stage.py','Dockerfile.detector','Dockerfile.recognition']]
paths += sorted((root/'workers/vendor').rglob('*.py'))
for path in paths:
    h.update(path.relative_to(root).as_posix().encode()); h.update(path.read_bytes())
print('real-v1-'+h.hexdigest()[:16])
