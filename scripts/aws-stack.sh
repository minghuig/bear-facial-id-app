#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
ACTION=${1:-help}
if [ "$ACTION" = plan ]; then
  terraform -chdir=infra init
  terraform -chdir=infra plan -out=proposal.tfplan
  exit
fi
if [ "$ACTION" = apply ]; then
  [ "${2:-}" = --approved-spend ] || { echo 'Owner approval of docs/AWS_COST_PROPOSAL.md required; then add --approved-spend'; exit 1; }
  terraform -chdir=infra apply proposal.tfplan
  exit
fi
REGION=$(terraform -chdir=infra output -raw region)
INSTANCE=$(terraform -chdir=infra output -raw instance_id)
case "$ACTION" in
  tunnel) aws --region "$REGION" ssm start-session --target "$INSTANCE" --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}' ;;
  stop) aws --region "$REGION" ec2 stop-instances --instance-ids "$INSTANCE" ;;
  start) aws --region "$REGION" ec2 start-instances --instance-ids "$INSTANCE"; aws --region "$REGION" ec2 wait instance-status-ok --instance-ids "$INSTANCE" ;;
  logs) NAME=$(terraform -chdir=infra output -raw name); aws --region "$REGION" logs tail "/$NAME" --follow ;;
  *) echo 'Usage: scripts/aws-stack.sh plan|apply --approved-spend|tunnel|stop|start|logs'; exit 1 ;;
esac
