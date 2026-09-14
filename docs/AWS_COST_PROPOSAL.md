# AWS trial cost and approval

The owner-authorized delegate approved up to **$15 before tax for the first month**, **20 total running hours**, and a review after eight hours. After AWS rejected M6a under the Free Plan, the user explicitly selected the largest eligible option: **m7i-flex.large, 2 vCPU / 8 GiB**, in **us-east-2 (Ohio)**. No account-plan upgrade is required for this instance. Model capacity remains unmeasured.

| Resource | Allowance | List-price estimate |
|---|---|---:|
| EC2, including bootstrap/builds/inference | 20 hours at $0.09576/hour | $1.92 |
| Public IPv4, outbound access only | 20 hours at $0.005/hour | $0.10 |
| Encrypted gp3 root disk | 40 GiB-month | $3.20 |
| Encrypted gp3 database disk | 10 GiB-month | $0.80 |
| ECR image storage | 20 GB-month | $2.00 |
| Private S3 | 10 GB-month | $0.23 |
| S3 requests | 10k writes + 100k reads | $0.09 |
| CloudWatch logs | 1 GB ingestion/storage, seven-day retention | $0.53 |
| Outbound transfer allowance | 5 GB | $0.45 |
| **First-month estimate before credits/tax** | | **$9.32** |

Prices were checked against AWS's Ohio catalog on September 13, 2026. Free Plan eligibility does not mean unlimited use; applicable credits and account limits determine actual billing. The $15 limit is operator-enforced, not an AWS hard cap. Stop and discuss before expanding resources or the running-hour allowance.

The approved stack comprises one EC2 instance, a separate database EBS volume/attachment, private S3 with encryption/public-access blocking/TLS enforcement, three ECR repositories, one log group, an EC2 role/profile and policies, and six networking resources. The API, database and isolated workers share the host. No load balancer, NAT gateway, managed database, GPU or hosted frontend is included.

Stopping EC2 preserves data but EBS/ECR/S3/log storage continues consuming approximately $6.30/month at these allowances. Retention beyond the approved first month requires a decision. Never delete owner data automatically to enforce the budget. Database dumps share the database disk and are not disaster recovery.

The initial M6a apply created supporting resources but no instance. A subsequent plan created only the eligible instance, database disk and attachment; both applies used the same retained private Terraform state. No replacement or deletion was needed. The canonical saved plan is ignored under infra/; it must be regenerated and inspected before future changes.

Access is through authenticated Session Manager forwarding. The security group has no inbound rules; S3 public access is blocked. The account owner granted administrator access to the operator instead of installing the draft policies in docs/iam. That access does not expand the approved deployment scope.

Sources: [Ohio EC2 prices](https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/US%20East%20%28Ohio%29/Linux/index.json), [Free Tier instance eligibility](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html), [EBS](https://aws.amazon.com/ebs/pricing/), [S3](https://aws.amazon.com/s3/pricing/), [ECR](https://aws.amazon.com/ecr/pricing/), [VPC IPv4](https://aws.amazon.com/vpc/pricing/), [CloudWatch](https://aws.amazon.com/cloudwatch/pricing/).
