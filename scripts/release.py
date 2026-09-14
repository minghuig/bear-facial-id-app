#!/usr/bin/env python3
"""Deploy only committed source. No Docker or ML execution on the local machine."""
import argparse, json, pathlib, subprocess, tempfile, time
ROOT = pathlib.Path(__file__).resolve().parents[1]
def run(*args, **kw):
    return subprocess.check_output(args, text=True, **kw).strip()
def output(name): return run('terraform', '-chdir='+str(ROOT/'infra'), 'output', '-raw', name)
def aws(*args): return run('aws', '--region', region, *args)
p = argparse.ArgumentParser()
p.add_argument('ref', nargs='?', default='main')
p.add_argument('--approved-spend', action='store_true', help='Use only after owner approval of docs/AWS_COST_PROPOSAL.md')
a = p.parse_args()
if not a.approved_spend: p.error('Owner spending approval required; then supply --approved-spend')
commit = run('git', '-C', str(ROOT), 'rev-parse', '--verify', a.ref+'^{commit}')
# Archive the selected commit; dirty working files can never enter the upload.
region, bucket, instance, registry, name, volume = [output(k) for k in ('region','bucket','instance_id','registry','name','database_volume_id')]
with tempfile.TemporaryDirectory() as tmp:
    bundle = pathlib.Path(tmp)/'source.tar.gz'
    subprocess.run(['git','-C',str(ROOT),'archive','--format=tar.gz','-o',str(bundle),commit], check=True)
    aws('s3','cp',str(bundle),f's3://{bucket}/releases/{commit}/source.tar.gz','--only-show-errors')
    # Only safe validated scalar identifiers enter this command; source script comes from the commit.
    import re
    for value in (region,bucket,instance,registry,name,volume,commit):
        if not re.fullmatch(r'[a-zA-Z0-9./_-]+', value): raise ValueError('Unsafe infrastructure output')
    command = f'''set -eu
mkdir -p /opt/only-bears/releases/{commit}
aws s3 cp s3://{bucket}/releases/{commit}/source.tar.gz /opt/only-bears/releases/{commit}/source.tar.gz --region {region}
tar -xzf /opt/only-bears/releases/{commit}/source.tar.gz -C /opt/only-bears/releases/{commit}
bash /opt/only-bears/releases/{commit}/scripts/remote-release.sh {commit} {region} {bucket} {registry} {name} {volume}
'''
    params = pathlib.Path(tmp)/'params.json'
    params.write_text(json.dumps({'commands':[command],'executionTimeout':['7200']}))
    command_id = json.loads(aws('ssm','send-command','--instance-ids',instance,'--document-name','AWS-RunShellScript','--parameters','file://'+str(params),'--output','json'))['Command']['CommandId']
    print(f'Release {commit}; SSM command {command_id}', flush=True)
    while True:
        # Keep polling ASCII-only: legacy Windows CLI encodings can reject build logs.
        try: result = json.loads(aws('ssm','get-command-invocation','--command-id',command_id,'--instance-id',instance,'--query','{Status:Status,ResponseCode:ResponseCode}','--output','json'))
        except subprocess.CalledProcessError:
            time.sleep(5); continue
        if result['Status'] in ('Pending','InProgress','Delayed'):
            time.sleep(10); continue
        if result['Status'] != 'Success': raise SystemExit(f"Deployment failed: {result['Status']}; inspect SSM command {command_id}")
        print('Deployed commit: '+commit); break
