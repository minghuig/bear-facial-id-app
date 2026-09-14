"""Prepare ignored local prototype images. Usage: python scripts/prepare_comparison.py PHOTO_ROOT"""
import json, sys
from pathlib import Path
from PIL import Image, ImageOps
root = Path(__file__).resolve().parents[1]
out = root / 'frontend/public/demo-photos'
out.mkdir(parents=True, exist_ok=True)
manifest = {}
for folder in ['battle', 'cc', 'goucho', 'blond_anteater']:
    manifest[folder] = []
    for i, path in enumerate(sorted((Path(sys.argv[1])/folder).glob('*'))):
        if path.suffix.lower() not in ['.jpg','.jpeg','.png']: continue
        image = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
        image.thumbnail((1600,1600))
        name = f'{folder}-{i}.jpg'
        image.save(out/name, quality=88)
        manifest[folder].append({'id':f'{folder}-{i}', 'src':f'/demo-photos/{name}', 'label':path.name})
(root/'frontend/src/comparison/photos.json').write_text(json.dumps(manifest, indent=2))
print({k:len(v) for k,v in manifest.items()})
