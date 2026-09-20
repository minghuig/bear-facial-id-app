#!/usr/bin/env python3
"""Prepare private local CPU configuration; no AWS credentials or model loading."""
import argparse
import importlib.util
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(models):
    spec = importlib.util.spec_from_file_location('verify_models', ROOT / 'scripts/verify-models.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify(models)


def prepare(root, models, pipeline, owner_settings=False):
    models = models.resolve()
    if any(c in str(models) for c in "\r\n'$"):
        raise ValueError('Model directory cannot contain newlines, quotes or dollar signs')
    verify(models)
    if not pipeline.startswith('real-v1-'):
        raise ValueError('Expected a content-derived real pipeline')
    path = root / '.env.local-real'
    values = {}
    if path.exists():
        values = dict(line.split('=', 1) for line in path.read_text().splitlines()
                      if '=' in line and not line.startswith('#'))
    for key in ('DB_PASSWORD', 'WORKER_TOKEN', 'MINIO_ROOT_PASSWORD'):
        values.setdefault(key, secrets.token_hex(24))
    values.update(
        DATABASE_URL=f"postgresql+psycopg://bears:{values['DB_PASSWORD']}@db/bears",
        ENVIRONMENT='local', PIPELINE=pipeline, S3_ENDPOINT='http://minio:9000',
        S3_BUCKET='only-bears', AWS_REGION='us-east-2',
        CORS_ORIGIN='http://localhost:5174', MINIO_ROOT_USER='local-bears',
        AWS_EC2_METADATA_DISABLED='true', LOCAL_MODELS_DIR=f"'{models.as_posix()}'",
    )
    if owner_settings:
        values['LOCAL_OWNER_SETTINGS'] = 'true'
    path.write_text(''.join(f'{key}={value}\n' for key, value in values.items()), newline='\n')
    path.chmod(0o600)
    return values


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, default=ROOT / '.private/models')
    parser.add_argument('--owner-settings', action='store_true', help='Enable local-only member settings')
    args = parser.parse_args()
    pipeline = subprocess.check_output([sys.executable, str(ROOT / 'scripts/pipeline.py')], text=True).strip()
    prepare(ROOT, args.models, pipeline, owner_settings=args.owner_settings)
    print('Verified four checkpoints; prepared .env.local-real (existing credentials preserved).')
