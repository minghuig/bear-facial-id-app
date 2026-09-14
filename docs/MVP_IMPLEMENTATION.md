# MVP implementation checkpoint

Branch: codex/mvp-accounts. Nothing in this branch has been deployed publicly.

Owner amendment: two organizations, Internal Testing and McNeil, CloudFront hostname initially. Existing records migrate to Internal Testing; McNeil begins empty. Both supplied Gmail accounts are invited to both through the operator CLI, not embedded as application defaults. The original single-org plan is superseded on this point.

Implemented foundation: per-org database ownership, digest uniqueness/storage keys, scoped browser queries/writes, org-specific gallery matching and worker outputs; Google OIDC login, opaque expiring/revocable sessions, CSRF checks, stale-tab org guard, account switcher, invitation CLI and frontend upload size checks. Public startup requires Google credentials and HTTPS origin. Current tunnel deployment remains unchanged.

Setup still required: Google Cloud web OAuth client owned by the project owner. Request only openid/email/profile. Use the eventual CloudFront URL plus /auth/callback exactly. Client secret and a random 32+ character cookie secret belong only in restricted runtime.env, never chat or Git. Configure AUTH_MODE=google, PUBLIC_DEPLOYMENT=true, PUBLIC_ORIGIN and CORS_ORIGIN to the same HTTPS URL. The provided compose.public.yaml fails closed when required values are absent.

After migration, invoke python -m app.manage_members invite ORG EMAIL once for each org/account pair. Operator removal revokes access; there is no separate in-app admin role. Google live sign-in is not yet verified; focused local tests use synthetic identities and reject invalid callback state.

CloudFront design review recommends pay-as-you-go distribution → VPC origin → Caddy:8080. No ALB/NAT/new instance. Forward cookies/query strings/needed headers, allow API methods, disable caching initially. Caddy blocks worker routes; PostgreSQL, direct API and S3 stay private. Verify VPC-origin eligibility for this existing subnet/account before applying; do not silently replace EC2 or remove its outbound route. The current Free flat-rate CloudFront plan is not equivalent to usage pricing with free allowances. Use the generated distribution HTTPS hostname for OAuth, subject to Google console validation.

Prepared frontend Dockerfile and Caddy/Compose overlay are not yet wired into release automation or provisioned. Public rollout must integrate auth, add web ECR/build/deploy steps, produce and approve an exact Terraform plan, and validate that cookies never traverse a public unencrypted origin connection. Custom domain can be added later by changing configured origin/callback/DNS/TLS, not data ownership.

Remaining MVP implementation: deletion with active-worker/preview fencing and retryable S3 cleanup; full Google callback success fixture/live owner setup; public release integration and narrow multi-account browser checks. Backups/full regression/load acceptance remain reliability work as agreed.

Cost decision: previous 20-hour/$15 trial is unchanged. At the already-verified Ohio rate of $0.09576/hour, 730 EC2 hours alone are about $69.90; IPv4 adds $3.65 and the existing disk/storage allowances roughly $7. A continuously running month is therefore roughly $80 before tax/credits and variable usage. This is a planning estimate, not a hard cap or provisioning approval. Present the exact current infrastructure diff, CloudFront plan eligibility and spending/runtime proposal before applying. Short scheduled availability can reduce EC2 cost.

Sources: https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html ; https://aws.amazon.com/cloudfront/pricing/ ; https://developers.google.com/identity/protocols/oauth2/web-server#uri-validation
