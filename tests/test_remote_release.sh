#!/bin/bash
# Run in a disposable, network-disabled container as root, with repository mounted read-only.
# Exercises the real release script; mocks only machine/AWS/Docker boundaries.
set -euo pipefail
ROOT=${1:-/repo}
export LOG=/tmp/release-operations CASE
mkdir -p /opt/only-bears/releases/test /opt/only-bears/models /srv/only-bears/backups
touch /opt/only-bears/models/fixture.pth /opt/only-bears/models/fixture.pb
cat > /srv/only-bears/runtime.env <<'ENV'
DB_PASSWORD=test
WORKER_TOKEN=test
ENV
function [() {
  if [[ ${1:-} == -b ]]; then return 0; fi
  builtin [ "$@"
}
cloud-init() { :; }
uname() { echo x86_64; }
blkid() { echo fixture-uuid; }
mountpoint() { :; }
systemctl() { :; }
aws() { echo 'aws' "$@" >> "$LOG"; }
python3() {
  if [[ $* == *scripts/pipeline.py* ]]; then echo fixture-pipeline;
  elif [[ $* == *verify-models.py* ]]; then
    echo verify-models >> "$LOG"
    [[ $CASE != invalid_models ]]
  else command python3 "$@"; fi
}
docker() {
  echo 'docker' "$@" >> "$LOG"
  case " $* " in
    *' login '*) cat >/dev/null ;;
    *' stop '*) [[ $CASE != stop_failure ]] ;;
    *' ps '*) [[ $CASE != first_install ]] && echo existing-writer; return 0 ;;
    *' pg_dump '*) echo fixture-backup ;;
  esac
}
curl() { printf '{"commit":"test"}\n'; }
export -f '[' cloud-init uname blkid mountpoint systemctl aws python3 docker curl
failures=0
for CASE in stop_failure first_install existing_install invalid_models public_install; do
  if [[ $CASE == public_install ]]; then
    export PUBLIC_DEPLOYMENT=true PUBLIC_ORIGIN=https://fixture.cloudfront.net GOOGLE_CLIENT_ID=fixture GOOGLE_CLIENT_SECRET=fixture OAUTH_COOKIE_SECRET=fixture
  fi
  : > "$LOG"
  set +e
  bash "$ROOT/scripts/remote-release.sh" test us-east-2 bucket registry only-bears vol-test > /tmp/release-output 2>&1
  result=$?
  set -e
  if [[ $CASE == public_install ]] && ! grep -q 'compose .*compose.public.yaml.*up -d api body-detector detector recognition web' "$LOG"; then
    echo 'FAIL: public release must use auth overlay and start web'; failures=$((failures+1))
  fi
  case $CASE in
    stop_failure)
      if (( result == 0 )) || grep -Eq 'pg_dump|alembic|compose .* up ' "$LOG"; then
        echo 'FAIL: failed writer stop must abort before database start, backup, migration or app start'; failures=$((failures+1))
      else echo 'PASS: writer stop failure aborts'; fi ;;
    invalid_models)
      if (( result == 0 )) || grep -Eq 'docker|ecr' "$LOG"; then
        echo 'FAIL: invalid checkpoint must abort before image authentication, build or release'; failures=$((failures+1))
      else echo 'PASS: invalid checkpoint aborts'; fi ;;
    *)
      if (( result != 0 )) || ! grep -q 'alembic upgrade head' "$LOG" || ! grep -q 'up -d api body-detector detector recognition' "$LOG"; then
        echo "FAIL: $CASE must back up, migrate and start successfully (exit $result)"; cat /tmp/release-output; failures=$((failures+1))
      else echo "PASS: $CASE releases successfully"; fi ;;
  esac
done
exit "$failures"
