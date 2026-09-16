import hashlib
import os
from pathlib import Path
HASHES = {
 'katmai_6y_net_best.pth':'6b9c43bb6f82d5a16c12a91258629e33656ad851a2626cc91baafbb82bea0cd3',
 'hrnet_w48_balanced_n13_refined.pth':'c38592c8928e481a7adad7e140aae8c3e1f219702d42de71d524a7da5daa7ca8',
 'bear_head_detector_latest.pth':'971cd05ebeb4982c271b4d8402514599435a93b20b3179ce9a70e7b916a9f657',
 'md_v4.1.0.pb':'0527840919699c0c329042a1c915e9ec0c758067677c6bf48b7978a36cb71413',
}
def checkpoint(name):
    path=Path(os.environ.get('MODEL_DIR','/models'))/name
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): digest.update(block)
    if digest.hexdigest()!=HASHES[name]: raise RuntimeError('Untrusted checkpoint: '+name)
    return path
