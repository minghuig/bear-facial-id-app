"""DB-free worker protocol; ML imports only in real stage adapters."""
import concurrent.futures
import os
import json
import subprocess
import sys
import time
import httpx
from process_error import describe

API = os.environ.get('API_URL','http://api:8000')
MODE = os.environ.get('MODE','mock')
PIPELINE = os.environ['PIPELINE']
STAGE = os.environ.get('STAGE')
if MODE == 'mock' and (os.environ.get('ENVIRONMENT') != 'local' or not PIPELINE.startswith('mock')):
    raise RuntimeError('Mock worker is local-only')
if MODE not in ('mock','real'): raise RuntimeError('Unknown worker mode')
client = httpx.Client(base_url=API,headers={'Authorization':'Bearer '+os.environ['WORKER_TOKEN']},timeout=60)

def mock(job):
    name = job['filename'].lower()
    if name.startswith('fail-detection') and job['stage'] == 'detection' and job['attempt'] == 1:
        raise RuntimeError('Deterministic first-attempt detection failure')
    if job['stage'] == 'detection':
        w,h = job['width'],job['height']
        boxes = [] if name.startswith('no-head') else [[w*.1,h*.1,w*.45,h*.7,.95]]
        if name.startswith(('multi','partial')): boxes.append([w*.55,h*.15,w*.95,h*.75,.9])
        return {'detection':{'width':w,'height':h,'boxes':boxes}}
    heads = []
    for index, head in enumerate(job['heads']):
        if name.startswith('partial') and index == 1 and job['attempt'] == 1:
            heads.append({'observation_id':head['observation_id'],'error':'Mock crop failure'}); continue
        # first/later fixtures deliberately represent the same individual.
        v = [0.0]*512; v[1 if name.startswith('different') else 0] = 1.0
        heads.append({'observation_id':head['observation_id'],'embedding':v,'diagnostics':{'fixture':name}})
    return {'heads':heads}

def execute(job):
    if MODE == 'mock': return mock(job)
    # One short-lived process per real job releases model RAM between stages.
    # Both real workers share a lock volume, serializing expensive inference.
    import fcntl
    lock_path = os.environ.get('WORKER_LOCK', '/locks/inference.lock')
    with open(lock_path, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        completed = subprocess.run([sys.executable, 'run_stage.py', job['stage']],
                                   input=json.dumps(job), text=True, capture_output=True,
                                   timeout=1500, check=True)
    return json.loads(completed.stdout)

def main():
    stages = [STAGE] if STAGE else ['detection','recognition']
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        while True:
            try:
                for stage in stages:
                    response = client.post('/internal/jobs/claim',json={'stage':stage,'pipeline':PIPELINE})
                    response.raise_for_status(); job = response.json()
                    if not job: continue
                    started = time.monotonic()
                    future = pool.submit(execute,job)
                    while not future.done():
                        try: future.result(timeout=30)
                        except concurrent.futures.TimeoutError:
                            beat = client.post(f"/internal/jobs/{job['job_id']}/heartbeat",json={'token':job['token']})
                            if beat.status_code == 409: os._exit(2)  # kill stuck ML; lease recovery handles restart
                            beat.raise_for_status()
                        except Exception: break
                    result = {'token':job['token'],'pipeline':PIPELINE,
                              'provenance':{'mode':MODE,'seconds':time.monotonic()-started,'commit':os.getenv('RELEASE_COMMIT','development')}}
                    try: result.update(future.result())
                    except subprocess.CalledProcessError as e: result['error'] = describe(e)
                    except Exception as e: result['error'] = str(e)[:2000]
                    response = client.post(f"/internal/jobs/{job['job_id']}/result",json=result)
                    response.raise_for_status()
                    print({'job':job['job_id'],'stage':stage,'seconds':time.monotonic()-started,'error':result.get('error')},flush=True)
                time.sleep(2)
            except httpx.HTTPError as e:
                print(type(e).__name__,str(e).split('?')[0],flush=True); time.sleep(5)
if __name__ == '__main__': main()
