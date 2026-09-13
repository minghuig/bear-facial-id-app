import hashlib
import os
from pathlib import Path
HASHES = {
 'test_on_2020_net_60.pth':'0a28bfa3cd5354526e692151659726c62a160c6d1499400ef783753192e8e8de',
 'hrnet_w48_balanced_n13_refined.pth':'c38592c8928e481a7adad7e140aae8c3e1f219702d42de71d524a7da5daa7ca8',
 'bear_head_detector_latest.pth':'971cd05ebeb4982c271b4d8402514599435a93b20b3179ce9a70e7b916a9f657',
}
def checkpoint(name):
    path=Path(os.environ.get('MODEL_DIR','/models'))/name
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): digest.update(block)
    if digest.hexdigest()!=HASHES[name]: raise RuntimeError('Untrusted checkpoint: '+name)
    return path
