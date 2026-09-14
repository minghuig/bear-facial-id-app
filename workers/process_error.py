"""Useful subprocess failures without exposing signed download parameters."""
import re


def describe(error):
    lines = (error.stderr or '').strip().splitlines()
    detail = lines[-1] if lines else 'No diagnostic output; check worker logs and host resources'
    detail = re.sub(r'(https?://[^\s?]+)\?\S+', r'\1?[redacted]', detail)
    return f'Inference process exited {error.returncode}: {detail}'[:2000]
