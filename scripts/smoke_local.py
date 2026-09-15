#!/usr/bin/env python3
"""Test-only deterministic full-stack acceptance through HTTP."""
import argparse
import io
import json
import time
import uuid
from pathlib import Path
import httpx
from PIL import Image

parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:19000');parser.add_argument('--output',default='.private/mock-smoke.json');args=parser.parse_args()
c=httpx.Client(base_url=args.url,timeout=60)
def call(method,path,**kwargs):
    r=c.request(method,path,**kwargs);r.raise_for_status();return r.json()
def wait_for_api():
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        try:return call('GET','/health')
        except httpx.HTTPError:time.sleep(.5)
    raise AssertionError(f'Timed out waiting for {args.url}')
def wait(photo_id,predicate):
    deadline=time.monotonic()+90
    while time.monotonic()<deadline:
        p=call('GET','/api/photos/'+photo_id)
        if predicate(p):return p
        time.sleep(.5)
    raise AssertionError('Timed out: '+json.dumps(p))
run=uuid.uuid4().hex[:8]
def upload(prefix,color):
    image=Image.new('RGB',(320,240),color)
    image.putpixel((0,0),tuple(bytes.fromhex(run[:6])))
    b=io.BytesIO();image.save(b,format='PNG');data=b.getvalue()
    r=call('POST','/api/photos',files={'files':(prefix+'-'+run+'.png',data,'image/png')})
    assert 'id' in r['photos'][0],r
    return r['photos'][0]['id'],data
health=wait_for_api();assert health['pipeline'].startswith('mock'), 'Refuse synthetic smoke against real environment'
first,data=upload('first',(80,40,10))
p=wait(first,lambda p:p['detection_state']=='complete');assert len(p['heads'])==1
assert p['heads'][0]['recognition_state']=='not_requested'
assert all(j['stage']=='detection' for j in p['jobs'])
dup=call('POST','/api/photos',files={'files':('other-name.png',data,'image/png')});assert dup['photos'][0]['id']==first and dup['photos'][0]['duplicate']
# Save an explicit pause checkpoint. The external validation restarts services then checks it.
paused,_=upload('multi-paused',(90,60,40));p=wait(paused,lambda p:p['detection_state']=='complete');assert len(p['heads'])==2
call('POST',f'/api/photos/{first}/recognize')
p=wait(first,lambda p:p['heads'][0]['recognition_state']=='complete');h=p['heads'][0]
bear=call('POST','/api/bears',json={'name':None})
call('POST',f"/api/heads/{h['id']}/review",json={'state':'confirmed','bear_id':bear['id']})
call('PATCH',f"/api/bears/{bear['id']}",json={'name':'Smoke bear '+run})
later,_=upload('later',(81,41,11));wait(later,lambda p:p['detection_state']=='complete')
call('POST',f'/api/photos/{later}/recognize');p=wait(later,lambda p:p['heads'][0]['recognition_state']=='complete')
q=p['heads'][0];snap=q['suggestions'][0];assert any(x['bear_id']==bear['id'] and x['reference_id']==h['id'] for x in snap['candidates']),snap
other=call('POST','/api/bears',json={'name':'Corrected '+run})
call('POST',f"/api/heads/{h['id']}/review",json={'state':'confirmed','bear_id':other['id']})
call('POST',f"/api/heads/{q['id']}/refresh")
p=call('GET','/api/photos/'+later);assert p['heads'][0]['suggestions'][1]['id']==snap['id']
assert any(x['bear_id']==other['id'] for x in p['heads'][0]['suggestions'][0]['candidates'])
assert len(call('GET',f"/api/heads/{h['id']}/history"))==2
assert not call('GET',f"/api/bears/{bear['id']}/references")
nohead,_=upload('no-head',(12,15,18));p=wait(nohead,lambda p:p['detection_state']=='complete');assert not p['heads']
failed,_=upload('fail-detection',(12,13,14));p=wait(failed,lambda p:p['detection_state']=='complete');assert p['jobs'][0]['attempts']==2 and len(p['heads'])==1
partial,_=upload('partial',(21,31,41));wait(partial,lambda p:p['detection_state']=='complete');call('POST',f'/api/photos/{partial}/recognize')
p=wait(partial,lambda p:any(h['recognition_state']=='failed' for h in p['heads']));assert [h['recognition_state'] for h in p['heads']]==['complete','failed']
call('POST',f'/api/photos/{partial}/recognize');p=wait(partial,lambda p:all(h['recognition_state']=='complete' for h in p['heads']));assert len(p['heads'][0]['suggestions'])==1
report={'mode':'mock','run':run,'paused_photo':paused,'first_photo':first,'later_photo':later,'reference_head':h['id'],'passed':['upload/storage','deduplication','detection pause','explicit recognition','later retrieval','correction/history','immutable snapshots','unnamed rename','no-head','automatic retry','partial failure retry']}
Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
