"""Local inference probe; no AWS calls. Run using run.ps1, not directly."""
import argparse
import contextlib
import hashlib
import json
import pathlib
import resource
import sys
import time

p = argparse.ArgumentParser()
p.add_argument('stage', choices=['detection', 'recognition'])
p.add_argument('--reserve-mib', type=int, default=768)
p.add_argument('inputs', nargs='+')
a = p.parse_args()
# Touched anonymous pages approximate unavailable memory for OS/services.
# This is a budget reservation, NOT a full-stack/load test.
reserve = bytearray(a.reserve_mib * 1024 * 1024)
for i in range(0, len(reserve), 4096):
    reserve[i] = 1
sys.path.insert(0, '/source/workers')
from PIL import Image
records = []
for filename in a.inputs:
    started = time.monotonic()
    path = pathlib.Path(filename)
    with contextlib.redirect_stdout(sys.stderr):
        image = Image.open(path).convert('RGB')
        if a.stage == 'detection':
            from detector import boxes
            result = boxes(image)
            details = {'boxes': len(result), 'scores': [round(b[4], 6) for b in result]}
        else:
            from recognition import embed
            vector, diagnostics = embed(image)
            details = {'embedding_dimensions': len(vector), 'diagnostics': diagnostics}
    records.append({'input': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'size': list(image.size), 'seconds': round(time.monotonic()-started, 3), **details})
    print(json.dumps({'progress': records[-1]}), flush=True)
peak = pathlib.Path('/sys/fs/cgroup/memory.peak')
events = pathlib.Path('/sys/fs/cgroup/memory.events')
print(json.dumps({'stage': a.stage, 'reserve_mib': a.reserve_mib,
 'process_peak_rss_mib': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024, 2),
 'cgroup_peak_mib': round(int(peak.read_text())/1048576, 2) if peak.exists() else None,
 'memory_events': events.read_text() if events.exists() else None,
 'records': records}), flush=True)
