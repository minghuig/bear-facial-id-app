# MVP hosting deployment

Owner approved deployment after Free Plan verification. Apply in progress; public distribution initially disabled. Plan SHA-256: 7d1de5540d0da2eacf35fb1f16de24247cffaf2553478bd16a08fcf1f75f7bc5.

Four resources created: disabled CloudFront distribution using its AWS HTTPS hostname, private VPC origin to existing EC2, web ECR repository, and one security-group ingress rule allowing port 8080 only from CloudFront's service-managed security group. One existing instance-role policy updated to allow the web repository. No replacements/deletions, ALB, NAT gateway, extra EC2, custom domain, or public ingress. Actual VPC-origin support for this account/subnet must be confirmed during creation; failure stops work rather than silently changing account plan or network topology.

CloudFront stays disabled until Google redirects are configured and the authenticated release passes narrow access checks. The application stays on EC2, with photos in private S3. Google client configuration is saved locally but not yet transferred to AWS. The existing live portal is unchanged.

| First 30-day planning allowance | Before credits/tax |
|---|---:|
| EC2 m7i-flex.large, 730 h × $0.09576 | $69.90 |
| Public IPv4 retained for outbound connectivity, 730 h × $0.005 | $3.65 |
| Existing 50 GiB gp3 disks | $4.00 |
| ECR 21 GB-month including new web package | $2.10 |
| S3 10 GB plus small request allowance | $0.32 |
| CloudWatch 1 GB ingestion/storage | $0.53 |
| CloudFront / transfer planning reserve | $5.00 |
| Total planning allowance | $85.50 |

Owner approved deployment on the ACTIVE AWS FREE account with USD100 remaining credits reported and expiration March 13, 2027. The table estimates credit consumption, not an out-of-pocket bill. The earlier USD90 paid-budget request is withdrawn; no paid-plan upgrade or 730-hour runtime commitment is approved. Keep existing server for testing; scheduling and smaller-server alternatives remain separate decisions. No ALB, NAT, replacement instance, or account upgrade without approval.

The existing Ohio rates were verified September 13 in AWS_COST_PROPOSAL.md. [CloudFront usage pricing](https://aws.amazon.com/cloudfront/pricing/) and [free usage allowances](https://aws.amazon.com/cloudfront/faqs/) were checked for this proposal. CloudFront allowance is shared across the AWS account. Variable usage/storage may differ; the reserve is an estimate, not a provider guarantee.

Independent architecture review checked private origin, cache/cookie handling and resource ordering. The managed origin security-group lookup now waits for distribution creation. Terraform validate and a refreshed plan against the canonical state pass. Public-site enabling requires a separate reviewed plan with enabled=true; no unauthenticated release may be exposed.
