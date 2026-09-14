# Invite-only MVP plan

> Owner amendment: two isolated organizations (Internal Testing and McNeil), CloudFront hostname first; implementation authorized. Existing data belongs to Internal Testing. See [implementation checkpoint](MVP_IMPLEMENTATION.md) for the revised account boundary, review, setup and remaining work. The singleton-org/custom-domain passages below record the earlier reviewed plan and are superseded.

Revision 2 · September 13, 2026 · baseline a8dcdd4 · planning only, no deployment authorized by this document.

## Scope

Three to five people, individual Google logins, one organization with one shared library and one role. Every admitted person can upload, review, edit, and delete shared photos. No self-signup, organization switching, billing, role management, or invitation-email system. Existing photos and bears become the organization's library without copying data.

Backups/restore, stronger quotas/rate controls, observability expansion, model/legal review, full regression, load tests, and broad acceptance testing are deferred to the reliability milestone. BEAR-5/6 remain recorded there, not falsely completed. Keep existing backend upload limits (20 files, 25 MiB each); add matching frontend checks. Retain data until explicitly deleted through the app.

## Smallest architecture

Keep EC2, PostgreSQL, S3, and the serialized CPU workers. Add a Caddy container on the same instance to serve the production frontend and proxy same-origin API/auth requests. Use a domain, stable address, HTTPS, and automatic certificate renewal. Only 80/443 become public; no public API port 8000, database, Docker, or worker routes. Keep SSM for operator access. Caddy explicitly denies /internal/*; the API continues to require the worker token there. Public assets contain no private library data.

Use Google OpenID Connect authorization-code login through a maintained library (Authlib proposed), not hand-written token verification. Request only openid/email/profile. Validate issuer, audience, expiry, signature, state and nonce; use PKCE and exact configured redirect URLs. Identify users by Google sub, not mutable email. Allowlisting is application-side, independent of Google's test-user configuration.

Minimal database additions: singleton organization, users (Google sub), invite/membership records, and expiring server-side sessions. The existing global library is explicitly owned by this one organization; no multi-tenant schema or client-selected org IDs. Reject a second organization until a later scoped-data migration exists. Membership checks protect every /api route, image/preview/thumbnail route, and bearer-ID lookup. Never treat localhost or the SSM tunnel as an authentication bypass in the public deployment.

An operator maintains up to five invited Google identities through a small CLI over SSM; no admin role/UI. Bootstrap admission uses an exact verified Gmail or Google Workspace address and binds it to sub on first login. For a Google account using a third-party email, verify its sub with the owner before admission rather than trusting historical email verification. Removing a member blocks subsequent requests and revokes its sessions. Every admitted member has identical library permissions.

Store opaque session tokens as hashes in PostgreSQL; cookies are Secure, HttpOnly, SameSite=Lax, host-only, with a seven-day absolute expiry. Logout revokes the session. Require a session-bound CSRF token on all browser mutations (including logout/uploads/deletion), plus same-origin checks; do not rely on CORS alone. Clear frontend query caches on logout and return private/no-store responses for protected JSON/images in the public deployment. Worker signed S3 URLs remain worker-only; browser images go through authenticated API routes. OAuth secrets stay in restricted runtime configuration and never in Git/frontend/logs.

## Ordered work packages

| Step | Work | Completion evidence |
|---|---|---|
| 1. Account boundary | Add singleton org, invitations/memberships and sessions; Google login/logout/current-user endpoints; shared API/image guards and CSRF. Preserve existing data and local development through explicit local-only auth configuration that public startup rejects. | Local integration tests: invited identity admitted, uninvited denied, invalid OAuth rejected, revoked/expired/logged-out sessions denied, protected images and mutations denied anonymously, worker credentials cannot create a browser session. Record tested commit and test output. |
| 2. Shared app UX | Google sign-in/invite-only denial page, account/logout UI, frontend session expiry handling, upload checks, shared-library behavior. | Browser smoke with two invited accounts against the same records; an uninvited account sees no library. Sign-out clears displayed data; frontend rejects >20 files or >25 MiB before upload. |
| 3. Delete photos | Add explicit destructive confirmation and API deletion for any member. Immediately hide/tombstone the photo and its heads, exclude deleted references from matching, invalidate affected suggestions/gallery revision, and block stale worker results/retries. Purge originals, oriented images, crops and cached derivatives through an idempotent retryable cleanup job; delete associated application rows when cleanup finishes. Keep bear identities stable. Block an identical digest upload while deletion is pending. Serialize deletion against active detection and lazy preview writes; fence stale work, finish in-flight writers before the final purge, and only release the digest for re-upload after cleanup finishes. | Focused integration tests cover deletion during queued/running inference, stale callbacks, reference removal, inaccessible image URLs, storage-cleanup retry, identical-file re-upload during cleanup, late preview writes, and unaffected unrelated photos. No undeclared backup retention is promised. |
| 4. Public packaging | Build frontend into Caddy image, add its ECR repository and build/push/deploy steps to the release tooling, same-origin routing, TLS persistence, production auth configuration, secret injection, migration/release instructions. Prepare Terraform diff for stable address, only 80/443 ingress, and scoped s3:DeleteObject permission on photos/*, crops/* and previews/* (not models or releases). | Local/container routing checks prove /internal is inaccessible through proxy and no secrets in frontend; produce exact infrastructure/cost proposal before applying. Steps 1-3 must be integrated before opening ingress. |
| 5. Invite-only launch | User supplies domain/DNS and Google OAuth setup; operator seeds organization and invite list. Apply separately approved infrastructure changes and deploy tested commit; run narrowly scoped login/access/shared-library smoke checks. | Record deployed commit, HTTPS reachability, invited/uninvited/logout/image checks and one upload→detection→recognition flow. Only then share URL with invited users. |

Dependencies: 1 → 2 and 3; 1–3 → 4 integration → 5. Packaging preparation may run alongside account work; public exposure waits for integrated guards. No implementation dispatch as part of this planning request.

## User setup and retained decisions

Before implementation launch setup: choose a domain/subdomain, organization display name and the 3–5 invited Google addresses. User creates/configures Google OAuth web client and exact callback URL with our instructions; secrets are entered privately on the host. Check Google's current publishing/test-mode requirements during setup. We can prepare all code before these inputs arrive.

Before any public infrastructure change: present concrete Terraform diff and costs for the domain (if purchased), stable public IPv4, ongoing EC2/EBS/S3 and transfer. No ALB, RDS, Cognito, or extra inference instance planned. Existing $15/20-hour trial approval does not authorize always-on hosting; obtain a new budget/runtime approval. Also obtain approval for opening public 80/443 as part of that concrete proposal. Roll back by closing public ingress and reverting the application release; retain data, compatible migrations and SSM access. Do not revert to an unauthenticated public release.

## Review and references

Independent reviewer /root/mvp_plan_review reviewed revision 1. Revision 2 addresses its two findings and packaging clarification; see [review record](MVP_PLAN_REVIEW.md). Reviewer should check scope discipline, invite/session/image boundary, deletion races, release ordering and missing user decisions. Focused feature/access checks remain part of MVP implementation; broad reliability acceptance is deferred as requested.

Primary references: [Google OIDC](https://developers.google.com/identity/openid-connect/openid-connect), [Google identity validation](https://developers.google.com/identity/sign-in/web/backend-auth), [Caddy HTTPS](https://caddyserver.com/docs/automatic-https). Recheck library/provider setup details when implementing.
