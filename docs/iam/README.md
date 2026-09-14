# Only Bears permission approval

These are review drafts for account `102913100078`, Ohio `us-east-2`. These drafts were not installed: the account owner granted administrator access instead. Keep these as an optional future reduction of privileges, not a prerequisite to the already approved deployment. They supplement the existing read-only access; JSON syntax and resource scoping are reviewable, but effective authorization has not been tested by provisioning.

## Temporary provisioning

Review [provisioning-temporary.json](provisioning-temporary.json) with the exact saved plan and cost proposal. It allows the enumerated network/storage creation and configuration operations in Ohio, the selected m7i-flex.large instance/AMI, and only the named S3 bucket, ECR repositories, log group, and IAM role/profile. Network and storage IDs do not exist yet: those EC2 resource-type wildcards cover other resources of those types in this account/region, not only the future project resources. It does not grant public-ingress authorization, deletion, IAM user management, or general AdministratorAccess.

**This is elevated deployment trust, not a privilege-escalation-proof policy.** `iam:PutRolePolicy` can write an arbitrary inline policy on `only-bears`; combined with passing that role to EC2, a trusted operator could expand the host's permissions beyond the reviewed application policy. IAM cannot constrain the inline policy JSON to our Terraform source with this grant. Approve that power knowingly, attach only for the supervised reviewed apply, and remove the temporary policy afterward. It grants no authority to make unreviewed changes. Alternatively, the account owner can run the exact reviewed Terraform apply from this checkout and its single state location without delegating these IAM writes.

No successful read-only plan proves every create-time permission. If apply later encounters AccessDenied, stop and inspect the exact denied operation; do not attach AdministratorAccess or expand the policy silently. Existing organizational restrictions, permission boundaries, and other policies also affect effective access.

## Ongoing release and tunnel operations

After apply produces the instance ID, replace `INSTANCE_ID_AFTER_APPLY` in [operator-after-apply.template.json](operator-after-apply.template.json) with that exact ID, review the rendered JSON, then attach it to the authorized operator. Never replace it with `*`. This allows start/stop, release through `AWS-RunShellScript`, forwarding through `AWS-StartPortForwardingSession`, own-session management, and project-bucket uploads/reads. The SSM command permission permits root-equivalent commands on that host; this is an operator role, not access for an untrusted application user. SSM forwarding also permits selecting a port on that host; approved collaborators share this trust boundary. No public gateway is created.

Verify authorized access and denial for a principal lacking permission before declaring the service usable. Do not give the runtime deployment policy to someone who only needs checkpoint upload; the account owner can upload to the private bucket using her existing authority. Model files must pass the recorded SHA256 checks before builds or model loading.

Sources: [AWS EC2 action/resource authorization](https://docs.aws.amazon.com/service-authorization/latest/reference/list_ec2.html), [AWS Session Manager policy examples](https://docs.aws.amazon.com/systems-manager/latest/userguide/getting-started-restrict-access-quickstart.html), and [IAM PassRole considerations](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html). No policy has been installed or represented as an AWS-enforced cost limit.
