"""Subprocess boundary releases all model memory; stdout contains only JSON."""
import contextlib
import json
import sys
job = json.load(sys.stdin)
with contextlib.redirect_stdout(sys.stderr):
    if sys.argv[1] == 'body_detection':
        from body_detector import detect
        result = detect(job)
    elif sys.argv[1] == 'head_detection':
        from detector import detect
        result = detect(job)
    else:
        from recognition import recognize
        result = recognize(job)
print(json.dumps(result,allow_nan=False))
