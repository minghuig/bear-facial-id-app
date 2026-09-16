"""Released six-year PoseSwin ReID; separate pose model, flip-sum normalization."""
import io
from types import SimpleNamespace
import httpx
import numpy as np
from PIL import Image
from trusted import checkpoint
_model = None
_transform = None

def model():
    global _model, _transform
    if _model is None:
        import torch
        import torch.nn as nn
        import torchvision.transforms as T
        from vendor.backbones.pose_net import SimpleHRNet
        from vendor.backbones.swin_transformer import SwinTransformer
        from vendor.build_swint import ft_net_swin
        torch.set_num_threads(2)
        pose_path=checkpoint('hrnet_w48_balanced_n13_refined.pth')
        reid_path=checkpoint('katmai_6y_net_best.pth')
        device=torch.device('cpu')
        cfg=SimpleNamespace(MODEL=SimpleNamespace(AGG_POSE_FEATURE=True))
        pose=SimpleHRNet(48,13,str(pose_path),model_name='HRNet',resolution=(256,256),max_batch_size=1,device=device)
        backbone=SwinTransformer(img_size=224,patch_size=4,in_chans=3,num_classes=109,
            embed_dim=128,depths=[2,2,18,2],num_heads=[4,8,16,32],window_size=7,mlp_ratio=4.,
            qkv_bias=True,qk_scale=None,drop_rate=0.,attn_drop_rate=0.,drop_path_rate=.2,
            norm_layer=nn.LayerNorm,ape=False,patch_norm=True,use_checkpoint=False,
            fused_window_process=False,cfg=cfg,pose_model=pose)
        _model=ft_net_swin(class_num=109,return_feature=True,linear_num=512,cfg=cfg,model_ft=backbone)
        state=torch.load(reid_path,map_location='cpu',weights_only=True)
        if isinstance(state.get('state_dict'),dict): state=state['state_dict']
        state={k.removeprefix('module.'):v for k,v in state.items()}
        _model.load_state_dict(state,strict=True); _model.to(device).eval()
        _transform=T.Compose([T.Resize((224,224)),T.ToTensor(),T.Normalize([.485,.456,.406],[.229,.224,.225])])
    return _model

def embed(image):
    import torch
    import torch.nn.functional as F
    m=model(); x=_transform(image.convert('RGB')).unsqueeze(0)
    with torch.inference_mode():
        _,a,pa=m(x); _,b,pb=m(torch.flip(x,dims=[3]))
        e=F.normalize(a+b,p=2,dim=1)[0].cpu().numpy()
    if e.shape!=(512,) or not np.isfinite(e).all() or not np.isclose(np.linalg.norm(e),1,atol=1e-4):
        raise ValueError('Invalid embedding')
    return e,{'pose_original':float(pa.mean()),'pose_flipped':float(pb.mean())}

def recognize(job):
    heads=[]
    for head in job['heads']:
        row={'observation_id':head['observation_id']}
        try:
            response=httpx.get(head['url'],timeout=120); response.raise_for_status()
            e,diagnostics=embed(Image.open(io.BytesIO(response.content)))
            row.update(embedding=e.tolist(),diagnostics=diagnostics)
        except Exception as e: row['error']=str(e)[:2000]
        heads.append(row)
    return {'heads':heads}
