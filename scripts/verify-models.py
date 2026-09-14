#!/usr/bin/env python3
"""Verify checkpoint bytes before builds or deserialization; stdlib only."""
import argparse
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'workers'))
from trusted import HASHES


def verify(directory):
    for name, expected in HASHES.items():
        digest = hashlib.sha256()
        with (Path(directory) / name).open('rb') as checkpoint:
            for block in iter(lambda: checkpoint.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != expected:
            raise ValueError('Untrusted checkpoint: ' + name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    verify(parser.parse_args().directory)
    print('All three checkpoint hashes verified')
