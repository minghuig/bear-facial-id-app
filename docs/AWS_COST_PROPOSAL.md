# AWS spending proposal — awaiting owner approval

Prepared 2026-09-13. No infrastructure has been provisioned or real inference benchmarked. Region: **us-east-1**. This proposal is a bounded first experiment, not a verified claim that the models fit or that hosting is continuously available below $20/month.

Use one Linux x86 **t3a.xlarge (4 vCPU, 16 GiB)**, shared API/PostgreSQL and isolated detector/recognition containers. Execute inference sequentially with one global lock; release model memory after each job. Build containers sequentially on that same EC2 instance, never on the Mac. Standard CPU credits avoid additional surplus-credit charges but sustained CPU may be throttled. If 16 GiB, CPU time, or disk capacity is insufficient, stop and propose a new configuration before resizing.

| Resource / scope | Rate and allowance | Estimated monthly cost |
|---|---|---:|
| EC2, including bootstrap, builds and benchmarks | $0.1504/hour; **20 running hours total** | $3.01 |
| Ephemeral public IPv4 for outbound AWS/package access | $0.005/hour, same 20 hours | $0.10 |
| Encrypted gp3 root volume | 40 GiB × $0.08/GiB-month | $3.20 |
| Separate encrypted gp3 PostgreSQL volume | 10 GiB × $0.08/GiB-month | $0.80 |
| Private ECR images | Allow 20 GB × $0.10/GB-month | $2.00 |
| Private S3 originals, crops, models, source bundles | Allow 10 GB × $0.023/GB-month | $0.23 |
| S3 requests | Allow 10k writes + 100k reads | $0.09 |
| CloudWatch logs | Allow 1 GB ingestion + retained storage, 7-day retention | $0.53 |
| Outbound transfer contingency | Allow 5 GB at $0.09/GB; do not rely on free allowance | $0.45 |
| **Estimated total before tax** | Includes full month of retained storage | **$10.41** |

Request approval for **up to $15 before tax for the first month**, limited to the resources above and at most 20 total running EC2 hours. Stop after the first 8-hour build/validation session if unfinished; review progress before consuming the remaining approved hours. This is an operator-enforced budget, not an AWS hard billing cap. Track build time in SSM and compute running hours. Do not silently extend the trial, resize, add a GPU, or raise storage allowances. The $4.59 contingency covers rounding and modest unexpected requests, not a larger deployment.

Compute stopped: EBS ($4/month), ECR (up to $2/month), S3 (~$0.23/month) and retained logs continue billing, approximately **$6.3/month** at these allowances. No Elastic IP is reserved. A stopped instance has no EC2 running charge and releases its auto-assigned public IPv4. This proposal authorizes first-month retention only; arrange continued retention or an explicit data-preserving shutdown decision before the month ends. Do not delete owner data as a budget mechanism.

Always-on use would cost approximately **$109.79/month for compute alone** (730 hours), plus ~$3.65 IPv4 and storage: well over $20. The backend is unavailable while stopped. Start it for development sessions and stop it afterward. An always-available low-cost deployment is not established by this trial.

No NAT gateway, load balancer, managed database, hosted frontend, paid interface endpoints, custom KMS key, or GPU is provisioned. SSM standard EC2 management/port forwarding has no extra session fee. There is no managed backup subscription; pre-migration database dumps occupy the database volume and are not disaster recovery. Any S3 backup or EBS snapshot retention extension requires a proposal. Same-region S3/ECR-to-EC2 traffic has no transfer charge; user-facing downloads still consume outbound transfer. Registry retention is manual: monitor size and retain the active and previous releases; do not expire images supporting a rollback accidentally.

Official sources checked on the preparation date: [EC2 T3/T3a Linux US East rates](https://aws.amazon.com/ec2/instance-types/t3/), [gp3 baseline storage rate](https://aws.amazon.com/ebs/general-purpose/), [IPv4 pricing](https://aws.amazon.com/vpc/pricing/), [ECR rate and same-region transfer](https://aws.amazon.com/ecr/pricing/), [S3 pricing](https://aws.amazon.com/s3/pricing/), [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/), [Systems Manager pricing](https://aws.amazon.com/systems-manager/pricing/). Amounts exclude tax and AWS credits. Reconfirm region prices if provisioning is delayed.
