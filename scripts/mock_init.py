#!/usr/bin/env python3
"""Prepare private settings for the explicit test-only mock stack."""
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(root=ROOT):
    path = root / '.env.mock'
    if path.exists():
        return path, False
    template = root / '.env.mock.example'
    path.write_text(template.read_text().replace(
        'replace-with-at-least-24-random-characters', secrets.token_urlsafe(32)))
    path.chmod(0o600)
    return path, True


if __name__ == '__main__':
    path, created = prepare()
    print(f'{"Created" if created else "Preserved"} private {path.name}')
