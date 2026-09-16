"""Copy an explicit private allowlist; never execute checkpoints or change bear-id."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workers'))
from trusted import HASHES


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prototype', type=Path, default=ROOT.parent / 'bear-id')
    args = parser.parse_args()
    source = args.prototype.resolve()
    target = ROOT / '.private'
    if target.is_symlink():
        raise ValueError('Private destination cannot be a symlink')
    entries = []
    for name, expected in HASHES.items():
        if name == 'md_v4.1.0.pb':
            path = target / 'models' / name
        elif name == 'katmai_6y_net_best.pth':
            path = target / 'checkpoint-candidates' / name
        else:
            relative = 'artifacts/' + ('detectors/' if name.startswith('bear_head') else '') + name
            path = source / relative
        entries.append((path, 'models/' + name, expected))
    pilot = json.loads((source / 'artifacts/detector_pilot/manifest.json').read_text())
    field = json.loads((source / 'artifacts/field_photo_test_v1/manifest.json').read_text())
    assert len(pilot) == 12 and len(field['photos']) == 35
    for row in pilot:
        assert re.fullmatch(r'images/p\d{3}\.jpg', row['pilot_path'])
        entries.append((source / 'artifacts/detector_pilot' / row['pilot_path'],
                        'validation/pilot/' + row['pilot_path'], row['sha256']))
    for row in field['photos']:
        assert re.fullmatch(r'crops/q\d{3}\.jpg', row['crop_path'])
        entries.append((source / 'artifacts/field_photo_test_v1' / row['crop_path'],
                        'validation/field/' + row['crop_path'], row['crop_sha256']))
    for src, dst in [
        ('artifacts/detector_pilot/manifest.json', 'validation/pilot/manifest.json'),
        ('artifacts/detector_pilot_results/output/results.json', 'validation/pilot/results.json'),
        ('artifacts/field_photo_test_v1/manifest.json', 'validation/field/manifest.json'),
    ]:
        entries.append((source / src, dst, digest(source / src)))
    field_features = target / 'checkpoint-candidates/results/katmai_6y_field_embeddings.npz'
    entries.append((field_features, 'validation/field/katmai_6y_field_embeddings.npz',
                    digest(field_features)))
    # Verify everything before copying anything. Saved reports without upstream hashes
    # receive a transfer-integrity hash; this is not an independent authenticity claim.
    for path, dst, expected in entries:
        allowed_root = target if path.is_relative_to(target) else source
        if path.is_symlink() or not path.resolve().is_relative_to(allowed_root):
            raise ValueError('Unsafe source ' + str(path))
        if digest(path) != expected:
            raise ValueError('Checksum mismatch: ' + str(path))
        destination = target / dst
        if destination.exists() and digest(destination) != expected:
            raise ValueError('Refusing to overwrite different private artifact: ' + dst)
        if destination.resolve() != destination.absolute():
            raise ValueError('Symlink in destination: ' + dst)
    target.mkdir(mode=0o700, exist_ok=True)
    os.chmod(target, 0o700)
    report = {'source_commit': '4a9f5be8a57c7493096cab1b114dcd71489a3dbe',
              'megadetector_release': 'v4.1', 'files': []}
    for path, dst, expected in entries:
        destination = target / dst
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            shutil.copyfile(path, destination)
        os.chmod(destination, 0o600)
        assert digest(destination) == expected
        report['files'].append({'path': dst, 'sha256': expected, 'bytes': destination.stat().st_size})
    manifest = target / 'package-manifest.json'
    manifest.write_text(json.dumps(report, indent=2) + '\n')
    os.chmod(manifest, 0o600)
    print(f'Verified {len(entries)} private files in {target}; no inference executed.')


if __name__ == '__main__':
    main()
