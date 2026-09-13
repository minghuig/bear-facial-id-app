"""AWS-only extracted-runner regression. Run in each stage's isolated image."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import time
import urllib.request


def aws_identity():
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('Real validation requires AWS Linux x86_64; never run on the Mac')
    # IMDSv2 is checked before importing any ML dependencies. No env bypass.
    base = 'http://169.254.169.254/latest/'
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    token = opener.open(urllib.request.Request(base + 'api/token', method='PUT', headers={
        'X-aws-ec2-metadata-token-ttl-seconds': '60'}), timeout=3).read().decode()
    return json.loads(opener.open(urllib.request.Request(base + 'dynamic/instance-identity/document',
        headers={'X-aws-ec2-metadata-token': token}), timeout=3).read())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['detection', 'recognition'])
    parser.add_argument('--private', type=Path, default=Path('/private'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    identity = aws_identity()
    report = {'stage': args.stage, 'status': 'running', 'instance_type': identity['instanceType'],
              'region': identity['region'], 'release_commit': os.environ.get('RELEASE_COMMIT', 'unrecorded'),
              'rows': [], 'versions': {}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    def save():
        report['seconds_total'] = time.perf_counter() - start
        report['process_peak_rss_mib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        report['memory_note'] = 'Linux process peak RSS includes model loading; not total host/container memory.'
        for path in ['/sys/fs/cgroup/memory.peak', '/sys/fs/cgroup/memory.max']:
            if Path(path).exists():
                report[Path(path).name] = Path(path).read_text().strip()
        args.output.write_text(json.dumps(report, indent=2) + '\n')
    try:
        for entry in json.loads((args.private / 'package-manifest.json').read_text())['files']:
            path = args.private / entry['path']
            if not path.resolve().is_relative_to(args.private.resolve()):
                raise ValueError('Unsafe artifact path')
            h = hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
            if h.hexdigest() != entry['sha256']: raise ValueError('Artifact transfer checksum mismatch')
        os.environ['MODEL_DIR'] = str(args.private / 'models')
        import numpy as np
        from PIL import Image, ImageOps
        for package in ['torch', 'torchvision', 'numpy', 'Pillow', 'mmcv-full', 'mmdet', 'timm']:
            try: report['versions'][package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError: pass
        root = args.private / 'validation'
        if args.stage == 'recognition':
            from recognition import embed
            with np.load(root / 'field/field_embeddings.npz', allow_pickle=False) as saved:
                expected = dict(zip(saved['query_id'].astype(str), saved['feature']))
            manifest = json.loads((root / 'field/manifest.json').read_text())['photos']
            assert len(expected) == len(manifest) == 35
            for row in manifest:
                before = time.perf_counter()
                with Image.open(root / 'field' / row['crop_path']) as image:
                    actual, diagnostics = embed(image)
                reference = expected[row['query_id']]
                assert reference.shape == (512,) and np.isfinite(reference).all() and np.linalg.norm(reference) > 0
                cosine = float(actual @ (reference / np.linalg.norm(reference)))
                report['rows'].append({'id': row['query_id'], 'cosine': cosine, 'passed': cosine >= .999,
                                       'seconds': time.perf_counter() - before, 'diagnostics': diagnostics})
                save()
        else:
            from detector import boxes
            expected = json.loads((root / 'pilot/results.json').read_text())['images']
            assert len(expected) == 12
            report['tolerances'] = {'coordinates_pixels': 1.0, 'score_absolute': .001, 'counts_exact': True}
            for row in expected:
                before = time.perf_counter()
                with Image.open(root / 'pilot/images' / row['image']) as source:
                    image = ImageOps.exif_transpose(source).convert('RGB')
                actual = np.asarray(boxes(image), dtype=float).reshape(-1, 5)
                reference = np.asarray(row['all_detections'], dtype=float).reshape(-1, 5)
                passed = actual.shape == reference.shape and image.size == (row['width'], row['height'])
                delta = None
                if passed:
                    delta = np.max(np.abs(actual-reference), axis=0).tolist() if len(actual) else [0]*5
                    passed = max(delta[:4]) <= 1 and delta[4] <= .001 and int((actual[:,4] >= .5).sum()) == len(row['displayed'])
                report['rows'].append({'id': row['image'], 'passed': bool(passed), 'max_abs_delta': delta,
                    'detections': actual.tolist(), 'seconds': time.perf_counter() - before})
                save()
        report['status'] = 'passed' if all(row['passed'] for row in report['rows']) else 'failed'
    except Exception as exc:
        report.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        save()
    if report['status'] != 'passed': raise SystemExit('Regression failed; inspect report')
    print(f'{args.stage}: passed {len(report["rows"])} regressions; report {args.output}')


if __name__ == '__main__':
    main()
