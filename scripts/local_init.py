#!/usr/bin/env python3
import secrets
from pathlib import Path
root=Path(__file__).resolve().parents[1]
path=root/'.env'
if path.exists():
    print('.env already exists; preserved')
else:
    path.write_text((root/'.env.example').read_text().replace('replace-with-at-least-24-random-characters',secrets.token_urlsafe(32)))
    path.chmod(0o600)
    print('Created private local .env')
