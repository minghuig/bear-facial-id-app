# MVP deployment checkpoint

Release branch: codex/mvp-accounts. EC2 release: 1d2e18f (includes approved library browser and branding). CloudFront: https://d1u7h1fs60yvpr.cloudfront.net, distribution EKI9LZWOO8UM6, private origin vo_1qIBWaAzgJbCPjcIQGjMdz. Public enablement completed. HTTPS checks: app 200, unauthenticated auth/me and photos 401, internal/docs 404; Google login 302 to accounts.google.com with Secure/HttpOnly cookie.

Google login and two isolated organizations are installed. Existing library migrated to Internal Testing; McNeil starts empty. zfleischman@gmail.com and minghuig@gmail.com are invited to both. Owner saved the exact /auth/callback redirect. Credentials were explicitly approved for temporary encrypted private S3 transfer, installed on EC2, and the temporary S3 copy deleted. Never commit or print runtime.env or google.env.

Validation: integrated frontend build and 22 focused account/migration/photo tests passed; five release-script cases passed. Live gateway returns 200 for the app, 401 for unauthenticated auth/me and API, 404 for internal worker routes/docs/health. Initial Caddy SPA fallback ordering was fixed in 1d2e18f. Successful real Google sign-in and organization switching still require owner browser verification.

Infrastructure uses existing Ohio EC2/Postgres/private S3 plus web ECR and pay-as-you-go CloudFront VPC origin. No ALB, NAT, custom domain, replacement instance, or account upgrade. Canonical Terraform state remains the main checkout infra/terraform.tfstate. Run Terraform from this branch using that explicit state path and enable_public_mvp=true/public_site_enabled=true. Local ignored public.auto.tfvars records these flags. Main's older infrastructure config must not be applied against the expanded state until this branch is integrated.

During creation, temporary AWS credentials expired waiting for CloudFront. AWS completed creation; the actual Deployed distribution was retained by clearing Terraform's failed-wait taint before replanning. Final enable plan adds one private ingress rule and updates enabled in place; no replacements or deletions.

Cost: ACTIVE FREE plan verified with USD100 credits reported, ending March 13, 2027 or credit exhaustion. Owner approved deployment after clarification that roughly USD80/month continuous usage consumes credits, not an out-of-pocket Free Plan bill. No paid-plan upgrade or always-on monthly commitment. Existing limited testing runtime remains; scheduling is not implemented.

Remaining broader MVP scope: photo deletion with worker fencing and retryable S3 cleanup; live two-user sign-in checks. Backups/full regression/load acceptance remain deferred to reliability work.