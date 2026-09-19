# MVP deployment checkpoint

> Historical deployment checkpoint. The live comparison flow and photo/bear deletion are now in the app; the [README](../README.md) and [roadmap](../ROADMAP.md) describe the current state. The sign-in and organization-switching browser verification mentioned below was not recorded in this checkpoint, so confirm its status rather than assuming it passed or failed.

Release source: `main`. Accounts, local CPU tooling, comparison, identity correction, automatic return to the library, and the ranked candidate list are integrated. Each release verifies that the live health commit matches `main`. CloudFront: https://d1u7h1fs60yvpr.cloudfront.net, distribution EKI9LZWOO8UM6, private origin vo_1qIBWaAzgJbCPjcIQGjMdz. Public enablement completed. HTTPS checks: app 200, unauthenticated auth/me and photos 401, internal/docs 404; Google login 302 to accounts.google.com with Secure/HttpOnly cookie.

Google login and two isolated organizations are installed. Existing library migrated to Internal Testing; McNeil starts empty. zfleischman@gmail.com and minghuig@gmail.com are invited to both. Owner saved the exact /auth/callback redirect. Credentials were explicitly approved for temporary encrypted private S3 transfer, installed on EC2, and the temporary S3 copy deleted. Never commit or print runtime.env or google.env.

Validation: integrated frontend build and 22 focused account/migration/photo tests passed; five release-script cases passed. Live gateway returns 200 for the app, 401 for unauthenticated auth/me and API, 404 for internal worker routes/docs/health. Initial Caddy SPA fallback ordering was fixed in 1d2e18f. Successful real Google sign-in and organization switching still require owner browser verification.

Infrastructure uses existing Ohio EC2/Postgres/private S3 plus web ECR and pay-as-you-go CloudFront VPC origin. No ALB, NAT, custom domain, replacement instance, or account upgrade. Canonical Terraform state remains the main checkout infra/terraform.tfstate. Run Terraform from `main` with enable_public_mvp=true/public_site_enabled=true. The preserved, ignored infra/public.auto.tfvars records these flags. The merged account and local CPU worktrees/branches were removed after deployment; private local settings and reports were preserved.

During creation, temporary AWS credentials expired waiting for CloudFront. AWS completed creation; the actual Deployed distribution was retained by clearing Terraform's failed-wait taint before replanning. Final enable plan adds one private ingress rule and updates enabled in place; no replacements or deletions.

Cost: ACTIVE FREE plan verified with USD100 credits reported, ending March 13, 2027 or credit exhaustion. Owner approved deployment after clarification that roughly USD80/month continuous usage consumes credits, not an out-of-pocket Free Plan bill. No paid-plan upgrade or always-on monthly commitment. Existing limited testing runtime remains; scheduling is not implemented.

At the time of this checkpoint, photo deletion and live two-user sign-in checks remained. Photo and bear deletion have since been implemented; this document does not record completion of the real-user sign-in checks. Treat its cost and validation figures as dated observations, not a current AWS balance or release acceptance report.
