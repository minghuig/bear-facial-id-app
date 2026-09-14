#!/bin/bash
# Invoked only on the provisioned x86 AWS instance through SSM.
set -euo pipefail
[ "$(uname -m)" = x86_64 ]
COMMIT=$1 REGION=$2 BUCKET=$3 REGISTRY=$4 APP_NAME=$5 VOLUME=$6
cd "/opt/only-bears/releases/$COMMIT"
cloud-init status --wait
# Identify the durable volume by its EBS serial, never by enumeration order.
DEVICE="/dev/disk/by-id/nvme-Amazon_Elastic_Block_Store_${VOLUME//-/}"
for i in $(seq 1 60); do [ -b "$DEVICE" ] && break; sleep 2; done
[ -b "$DEVICE" ]
if ! blkid "$DEVICE"; then mkfs.ext4 "$DEVICE"; fi
mkdir -p /srv/only-bears
UUID=$(blkid -s UUID -o value "$DEVICE")
if ! grep -q "UUID=$UUID " /etc/fstab; then echo "UUID=$UUID /srv/only-bears ext4 defaults,nofail 0 2" >> /etc/fstab; fi
mountpoint -q /srv/only-bears || mount /srv/only-bears
mkdir -p /etc/systemd/system/docker.service.d
cat > /etc/systemd/system/docker.service.d/storage.conf <<'UNIT'
[Unit]
RequiresMountsFor=/srv/only-bears
UNIT
systemctl daemon-reload
mkdir -p /opt/only-bears/models /opt/only-bears/locks /srv/only-bears/backups
chmod 777 /opt/only-bears/locks
if [ ! -f /srv/only-bears/runtime.env ]; then
  umask 077
  DB_PASSWORD=$(openssl rand -hex 24)
  WORKER_TOKEN=$(openssl rand -hex 32)
  cat > /srv/only-bears/runtime.env <<ENV
DATABASE_URL=postgresql+psycopg://bears:$DB_PASSWORD@db/bears
DB_PASSWORD=$DB_PASSWORD
WORKER_TOKEN=$WORKER_TOKEN
ENVIRONMENT=aws
S3_BUCKET=$BUCKET
AWS_REGION=$REGION
CORS_ORIGIN=http://localhost:5173
ENV
fi
PIPELINE=$(python3 scripts/pipeline.py)
sed -i '/^PIPELINE=/d' /srv/only-bears/runtime.env
printf 'PIPELINE=%s\n' "$PIPELINE" >> /srv/only-bears/runtime.env
aws s3 sync "s3://$BUCKET/models/" /opt/only-bears/models/ --region "$REGION" --only-show-errors
python3 scripts/verify-models.py /opt/only-bears/models
chmod 755 /opt/only-bears/models
chmod 644 /opt/only-bears/models/*.pth
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"
# Build sequentially on AWS. Existing immutable commit tags are reused.
set -a
source /srv/only-bears/runtime.env
set +a
services=(api detector recognition)
compose_files=(-f infra/compose.aws.yaml)
if [ "${PUBLIC_DEPLOYMENT:-false}" = true ]; then
  : "${PUBLIC_ORIGIN:?Public origin required}"
  : "${GOOGLE_CLIENT_ID:?Google client ID required}"
  : "${GOOGLE_CLIENT_SECRET:?Google client secret required}"
  : "${OAUTH_COOKIE_SECRET:?OAuth cookie secret required}"
  services+=(web)
  compose_files+=(-f infra/compose.public.yaml)
fi
for service in "${services[@]}"; do
  if ! aws ecr describe-images --region "$REGION" --repository-name "$APP_NAME/$service" --image-ids "imageTag=$COMMIT" >/dev/null 2>&1; then
    file="workers/Dockerfile.$service"
    [ "$service" != api ] || file=backend/Dockerfile
    [ "$service" != web ] || file=frontend/Dockerfile
    docker build -f "$file" -t "$REGISTRY/$APP_NAME/$service:$COMMIT" .
    docker push "$REGISTRY/$APP_NAME/$service:$COMMIT"
  fi
done
export RELEASE_COMMIT=$COMMIT AWS_REGION=$REGION REGISTRY APP_NAME
set -a
source /srv/only-bears/runtime.env
set +a
compose() { docker compose -p only-bears "${compose_files[@]}" "$@"; }
# Quiesce writers; preserve a pre-migration logical backup on the durable disk.
compose stop "${services[@]}"
compose up -d --wait db
compose exec -T db pg_dump -U bears -Fc bears > "/srv/only-bears/backups/pre-$COMMIT-$(date +%s).dump"
compose run --rm --no-deps api alembic upgrade head
compose up -d "${services[@]}"
for i in $(seq 1 60); do
  if curl -fsS http://localhost:8000/health > /tmp/only-bears-health.json; then
    python3 -c 'import json,sys; assert json.load(open("/tmp/only-bears-health.json"))["commit"]==sys.argv[1]' "$COMMIT"
    ln -sfn "/opt/only-bears/releases/$COMMIT" /opt/only-bears/current
    printf '%s\n' "$COMMIT" > /srv/only-bears/deployed-commit
    cat /tmp/only-bears-health.json
    exit 0
  fi
  sleep 2
done
exit 1
