#!/usr/bin/env python3
"""Download the pinned public MegaDetector v4.1 checkpoint and verify its bytes."""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
NAME = 'md_v4.1.0.pb'
SHA256 = '0527840919699c0c329042a1c915e9ec0c758067677c6bf48b7978a36cb71413'
URL = 'https://github.com/agentmorris/MegaDetector/releases/download/v4.1/md_v4.1.0.pb'


def digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


def download(directory):
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / NAME
    if target.exists():
        if target.is_symlink() or digest(target) != SHA256:
            raise ValueError(f'Refusing to overwrite untrusted checkpoint: {target}')
        return target, False
    with tempfile.NamedTemporaryFile(dir=directory, prefix=NAME + '.', delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            with urllib.request.urlopen(URL, timeout=120) as response:
                while chunk := response.read(1024 * 1024):
                    temporary.write(chunk)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
    try:
        if digest(temporary_path) != SHA256:
            raise ValueError('Downloaded MegaDetector checkpoint failed SHA-256 verification')
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)
    return target, True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--models', type=Path, default=ROOT / '.private/models')
    path, changed = download(parser.parse_args().models)
    print(('Downloaded and verified ' if changed else 'Already present and verified ') + str(path))
