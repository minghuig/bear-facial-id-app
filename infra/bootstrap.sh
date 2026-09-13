#!/bin/bash
set -euo pipefail
dnf install -y docker amazon-ssm-agent
systemctl enable --now docker amazon-ssm-agent
# Pin Compose; verify the upstream checksum before installation.
mkdir -p /usr/local/lib/docker/cli-plugins
curl -fsSL https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64 -o /tmp/docker-compose-linux-x86_64
curl -fsSL https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64.sha256 -o /tmp/docker-compose.sha256
cd /tmp
sha256sum -c docker-compose.sha256
install -m 755 docker-compose-linux-x86_64 /usr/local/lib/docker/cli-plugins/docker-compose
mkdir -p /opt/only-bears
