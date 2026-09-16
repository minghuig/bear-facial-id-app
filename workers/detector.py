"""Run the released head detector on padded body crops. AWS only."""
import io
import httpx
import numpy as np
from PIL import Image
from trusted import checkpoint
_model = None

def model():
    global _model
    if _model is None:
        import torch
        from mmcv import Config
        from mmdet.models import build_detector
        torch.set_num_threads(2)
        ckpt=torch.load(checkpoint('bear_head_detector_latest.pth'),map_location='cpu')
        cfg=Config.fromstring(ckpt['meta']['config'],'.py'); cfg.model.backbone.init_cfg=None
        _model=build_detector(cfg.model,test_cfg=cfg.get('test_cfg'))
        _model.load_state_dict(ckpt['state_dict'],strict=True)
        _model.cfg=cfg; _model.CLASSES=ckpt['meta']['CLASSES']; _model.to('cpu').eval()
    return _model

def boxes(image):
    import torch
    from mmdet.apis import inference_detector
    with torch.no_grad():
        # MMDetection ndarray input is BGR, matching its file loader.
        output=np.asarray(inference_detector(model(),np.asarray(image)[:,:,::-1].copy())[0])
    if not np.isfinite(output).all(): raise ValueError('Nonfinite detection')
    return output.tolist()

def detect(job):
    results=[]
    for body in job['bodies']:
        response=httpx.get(body['url'],timeout=120); response.raise_for_status()
        image=Image.open(io.BytesIO(response.content)).convert('RGB')
        if (image.width,image.height)!=(body['width'],body['height']):
            raise ValueError('Body crop dimensions do not match job metadata')
        results.append({'body_index':body['index'],'width':image.width,'height':image.height,
                        'boxes':boxes(image)})
    return {'head_detections':results}
