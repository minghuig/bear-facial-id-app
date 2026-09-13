"""Subprocess boundary releases all model memory; stdout contains only JSON."""
import contextlib
import json
import sys
job = json.load(sys.stdin)
with contextlib.redirect_stdout(sys.stderr):
    if sys.argv[1] == 'detection':
        from detector import detect
        result = detect(job)
    else:
        from recognition import recognize
        result = recognize(job)
print(json.dumps(result,allow_nan=False))
