#!/usr/bin/env python3
"""Verify private checkpoint hashes, then upload only the four required files."""
import argparse, hashlib, pathlib, subprocess, sys
root=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'workers'))
from trusted import HASHES
p=argparse.ArgumentParser()
p.add_argument('--approved-spend', action='store_true')
p.add_argument('--models', type=pathlib.Path, default=root/'.private/models')
a=p.parse_args()
if not a.approved_spend: p.error('Owner spending approval required first')
def output(key): return subprocess.check_output(['terraform','-chdir='+str(root/'infra'),'output','-raw',key],text=True).strip()
files=[]
for name,expected in HASHES.items():
    path=a.models/name
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    if h.hexdigest()!=expected: raise SystemExit('Checkpoint hash mismatch: '+name)
    files.append(path)
bucket,region=output('bucket'),output('region')
for path in files:
    subprocess.run(['aws','--region',region,'s3','cp',str(path),f's3://{bucket}/models/{path.name}','--only-show-errors'],check=True)
