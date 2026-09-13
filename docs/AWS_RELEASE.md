# Manual AWS operations

Status: implementation prepared; cloud deployment and real inference validation remain unperformed pending spending approval and access. See [cost proposal](AWS_COST_PROPOSAL.md). Never substitute local mocked results for the real acceptance checklist in the controlling plan.

## Prerequisites and access

Install Terraform >=1.6, AWS CLI v2, the AWS Session Manager plugin, Python 3 and Git on the operator machine. Docker is unnecessary for releasing: all container builds and all real inference happen on EC2. Authenticate the CLI to the approved AWS account using its normal SSO/credential mechanism (`aws sts get-caller-identity` confirms the account). Operator permissions must cover the Terraform resources plus SSM SendCommand/StartSession, S3 uploads and EC2 start/stop. These permissions are infrastructure/operator access, never application accounts or browser secrets.

The VPC allows **no inbound connections**. Its public address supports outbound installation and SSM; no API/SSH ports are publicly open. API binds to host loopback. Frontend remains at `http://localhost:5173`, and reaches AWS through authenticated SSM port forwarding to `http://localhost:8000`. S3 is private and uses expiring object links. Do not expose port 8000 or share a worker token with the frontend.

## First deployment

1. Review the committed Terraform and cost proposal. `bash scripts/aws-stack.sh plan` initializes Terraform and saves a plan without provisioning. Review it with `terraform -chdir=infra show proposal.tfplan`.
2. Obtain owner approval of the explicit dollar/hour/storage scope. Only then run `bash scripts/aws-stack.sh apply --approved-spend`.
3. Run `python3 scripts/upload-models.py --approved-spend`. It verifies all three trusted checkpoint hashes before uploading files from the sibling prototype. No labels, photos or generated embeddings are uploaded by this step. The prototype is read only.
4. Commit the application to `main`. Run **`python3 scripts/release.py --approved-spend`**. The command resolves `main` to an exact commit, uses `git archive`, uploads private source to S3, builds/publishes immutable commit tags in ECR remotely, backs up PostgreSQL, migrates, starts containers, verifies `/health`, and reports the deployed commit. It never includes uncommitted files. Explicit revision: `python3 scripts/release.py COMMIT_OR_REF --approved-spend`.
5. In a separate terminal: `bash scripts/aws-stack.sh tunnel`. Start the local frontend pointing at `http://localhost:8000`; keep that terminal open. Local API must be stopped so the tunnel can bind port 8000.
6. Execute the real validation checklist in `TRACER_BULLET_PLAN.md` section C and record timings/RSS, photos used and results in a private report. Prove the persisted pause across restart, eligible later-photo retrieval, corrections and redeployment. Do not mark complete until this passes.

The approval flag records operator intent, not proof of human approval. It must not be used before approval exists. The same Python release entry point can later run in GitHub Actions with AWS OIDC and approved roles; CI configuration is not required now.

## Logs, stop/start and failures

`bash scripts/aws-stack.sh logs` tails CloudWatch; the release prints its SSM command ID for build failures. Inspect a remote command with `aws ssm get-command-invocation --region us-east-1 --command-id COMMAND_ID --instance-id INSTANCE_ID`. Initial bootstrap logs are `/var/log/cloud-init-output.log`; use an SSM shell if needed. Build commands can take up to two hours and may exhaust standard CPU credits. Do not run a replacement ML build on the Mac.

`bash scripts/aws-stack.sh stop` stops compute. `bash scripts/aws-stack.sh start` restarts it; restart the tunnel after instance health is ready. Docker restart policies restart services; its mount dependency ensures the persistent database disk is mounted first. Images, source and models remain on the root volume across stop/start; PostgreSQL and runtime secrets are on a separate EBS volume. Container replacement does not remove data. EC2 replacement loses the root build cache but reuses the protected DB volume in the same availability zone; rerun release afterward.

If deployment fails after stopping services or migrating, the command exits nonzero and does not claim success. Inspect logs; fix and release another committed version. Releasing a previous commit reuses its immutable image tags, but **does not roll back migrations**. Only use a previous app version if compatible with the current schema. Pre-migration `pg_dump` files are `/srv/only-bears/backups`; restoring one discards subsequent writes and requires a deliberate owner decision. Never automatically downgrade or restore a database.

## State and durability

Terraform uses local state under `infra/`, ignored by Git. Keep it private and backed up to an approved encrypted location; losing state is not safe cleanup. A remote encrypted, locked state backend can be added when Actions is introduced. `prevent_destroy` protects S3 and the database volume; do not remove it to force teardown. Deleting compute, storage, checkpoints or stored decisions are separate operations. Root disk is disposable on termination, not the database disk. Database dumps on the same disk protect against migrations, not disk loss. Disaster recovery and unattended availability remain limitations.

Runtime secrets are generated on EC2, chmod 600, on the encrypted database disk; Terraform state contains no application passwords. The EC2 role is restricted to this application's bucket/registries/logs plus standard SSM. Containers use the instance role for S3, so this is a restricted development host, not isolation between hostile tenants. Images contain code only; checkpoints are read-only mounts from private S3. Before staff rollout resolve upstream licensing and production backup/security requirements documented in the prototype.
