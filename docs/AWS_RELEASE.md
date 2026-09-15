# Manual AWS operations

Status: infrastructure provisioned on m7i-flex.large in Ohio under the approved trial budget. Committed release is building; real inference and application acceptance remain pending.

Initial M6a launch was rejected by the Free Plan. The user authorized m7i-flex.large instead; Terraform reused the existing state and created only the remaining instance, database volume and attachment. Preserve the state; refresh and inspect any future plan.

## Prerequisites and access

Install Terraform >=1.6, AWS CLI v2, the AWS Session Manager plugin, Python 3 and Git on the operator machine. Docker is unnecessary for releasing: all container builds and all real inference happen on EC2. Authenticate the CLI to the approved AWS account using its normal SSO/credential mechanism (`aws sts get-caller-identity` confirms the account). Operator permissions must cover the Terraform resources plus SSM SendCommand/StartSession, S3 uploads and EC2 start/stop. These permissions are infrastructure/operator access, never application accounts or browser secrets.

The VPC allows **no inbound connections**. Its public address supports outbound installation and SSM; no API/SSH ports are publicly open. API binds to host loopback. The optional AWS-tunnel frontend uses `http://localhost:5173` and reaches AWS through authenticated SSM port forwarding to `http://localhost:8000`. Start it with `npm run dev:aws` from `frontend/`. S3 is private and uses expiring object links. Do not expose port 8000 or share a worker token with the frontend.

## First deployment

### Required authenticated-access gate

Before requesting provisioning approval, review the replacement saved plan and the exact release source together: no public ingress (including SSH), API published only on host loopback, no database or worker ports published, private S3 with public-access blocking, and operator Session Manager permissions limited to the approved instance and forwarding document. The user requires this review before deployment; spending approval remains a separate prerequisite.

The browser API has no application login. Its access boundary for this trial is the operator's AWS-authenticated SSM tunnel. CORS is not authentication. Anyone given tunnel access can use the application, so grant it only to approved collaborators. Worker bearer credentials must remain server-side. Expiring S3 links grant temporary access to their objects and must be treated as private links.

After approved infrastructure provisioning, but before releasing the application or uploading private inputs, verify the actual security group has no inbound rules and the actual bucket blocks public access. Before declaring the service usable, verify loopback-only listeners, successful forwarding by the authorized operator, denied forwarding for a principal without permission, and HTTP 401 for missing/incorrect worker credentials. Record exact commands and results; planned settings do not prove deployed enforcement. If any check fails, stop the release and correct the boundary. Public hosting would require a separately reviewed authentication design and approval.

1. Select Ohio explicitly: in PowerShell set `$env:TF_VAR_region = "us-east-2"`; in Bash use `export TF_VAR_region=us-east-2`. This follows the owner's latest region correction. The Terraform default is now Ohio and m7i-flex.large. Review the committed Terraform and cost proposal. `bash scripts/aws-stack.sh plan` initializes Terraform and saves a plan without provisioning. Review it with `terraform -chdir=infra show proposal.tfplan`.
2. Obtain owner approval of the explicit dollar/hour/storage scope. Only then run `bash scripts/aws-stack.sh apply --approved-spend`.
3. After actual private-bucket/no-ingress verification and successful bootstrap, stop EC2 while the owner uploads the three checkpoints to s3://only-bears-102913100078-us-east-2/models/. No running EC2 is needed for that upload. Restart when inputs are ready. The release verifies all three SHA256 values immediately after sync, before ECR authentication/build or model loading. The local upload-models.py helper remains optional when trusted local files exist.
4. Commit the application to `main`. Run **`python3 scripts/release.py --approved-spend`**. The command resolves `main` to an exact commit, uses `git archive`, uploads private source to S3, builds/publishes immutable commit tags in ECR remotely, backs up PostgreSQL, migrates, starts containers, verifies `/health`, and reports the deployed commit. It never includes uncommitted files. Only the current `main` commit may deploy. An explicit `COMMIT_OR_REF` must resolve to the same commit as local `main`; other revisions are rejected before any AWS calls. Merge and push `main` first, then run `python3 scripts/release.py main --approved-spend`, and verify the live health commit matches.
5. In a separate terminal: `bash scripts/aws-stack.sh tunnel`. Start the local frontend pointing at `http://localhost:8000`; keep that terminal open. Local API must be stopped so the tunnel can bind port 8000.
6. Execute the real validation checklist in `TRACER_BULLET_PLAN.md` section C and record timings/RSS, photos used and results in a private report. Prove the persisted pause across restart, eligible later-photo retrieval, corrections and redeployment. Do not mark complete until this passes.

The approval flag records operator intent, not proof of human approval. It must not be used before approval exists. The same Python release entry point can later run in GitHub Actions with AWS OIDC and approved roles; CI configuration is not required now.

## Logs, stop/start and failures

`bash scripts/aws-stack.sh logs` tails CloudWatch; the release prints its SSM command ID for build failures. Inspect a remote command with `aws ssm get-command-invocation --region us-east-2 --command-id COMMAND_ID --instance-id INSTANCE_ID`. Initial bootstrap logs are `/var/log/cloud-init-output.log`; use an SSM shell if needed. Build commands can take up to two hours; M7i-flex has a 40% CPU baseline; sustained build and inference timing must be measured. Do not run a replacement ML build on the Mac.

`bash scripts/aws-stack.sh stop` stops compute. `bash scripts/aws-stack.sh start` restarts it; restart the tunnel after instance health is ready. Docker restart policies restart services; its mount dependency ensures the persistent database disk is mounted first. Images, source and models remain on the root volume across stop/start; PostgreSQL and runtime secrets are on a separate EBS volume. Container replacement does not remove data. EC2 replacement loses the root build cache but reuses the protected DB volume in the same availability zone; rerun release afterward.

If deployment fails after stopping services or migrating, the command exits nonzero and does not claim success. Inspect logs; fix and release another committed version. Releasing a previous commit reuses its immutable image tags, but **does not roll back migrations**. Only use a previous app version if compatible with the current schema. Pre-migration `pg_dump` files are `/srv/only-bears/backups`; restoring one discards subsequent writes and requires a deliberate owner decision. Never automatically downgrade or restore a database.

## State and durability

Terraform uses local state under `infra/`, ignored by Git. Keep it private and backed up to an approved encrypted location; losing state is not safe cleanup. A remote encrypted, locked state backend can be added when Actions is introduced. `prevent_destroy` protects S3 and the database volume; do not remove it to force teardown. Deleting compute, storage, checkpoints or stored decisions are separate operations. Root disk is disposable on termination, not the database disk. Database dumps on the same disk protect against migrations, not disk loss. Disaster recovery and unattended availability remain limitations.

Runtime secrets are generated on EC2, chmod 600, on the encrypted database disk; Terraform state contains no application passwords. The EC2 role is restricted to this application's bucket/registries/logs plus standard SSM. Containers use the instance role for S3, so this is a restricted development host, not isolation between hostile tenants. Images contain code only; checkpoints are read-only mounts from private S3. Before staff rollout resolve upstream licensing and production backup/security requirements documented in the prototype.
