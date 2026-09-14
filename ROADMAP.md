# Roadmap

Only Bears is a hobby project for a small invited group. The next milestone is a usable shared-library MVP; reliability work follows. This is a direction and status guide, not a promise of delivery dates. Conductor tracks individual tickets.

## Available now

- Photo upload with progress, multiple files, and basic size/count limits.
- Automatic bear-head detection and queued recognition on CPU.
- Human review, confirmed references, similarity-ranked suggestions, and review history.
- Photo-library search, filters, pagination, and bear reference thumbnails.
- Hosted Google sign-in with invited accounts and separate Internal Testing / McNeil libraries.
- Local mock development and a separate real-CPU development branch.

The hosted account implementation lives on `codex/mvp-accounts`; it is not yet merged into `main`. Deployment checks pass, but real-user sign-in and organization-switching verification remain part of the MVP handoff.

## Next: shared-library MVP

Keep the scope small: individual Google accounts, one permission level, and equal access to photos within an organization.

- [ ] Complete real-user sign-in and organization-switching checks.
- [ ] Finish the welcoming sign-in page using the existing logo and a field photo.
- [ ] Add photo deletion, including safe handling of jobs still processing that photo and removal of stored objects.
- [ ] Bring the deployed account changes into the main development line.
- [ ] Evaluate the comparison/review prototype with users before integrating it.
- [ ] Set a practical hosting schedule or lower-cost arrangement within the approved Free Plan constraints.

An attractive prototype or a passing mock test does not by itself mean a feature is deployed or model accuracy is established.

## Later: reliability

These are intentionally deferred from the MVP:

- Storage/database backups and a tested restore procedure.
- Stronger server-side upload limits, quotas, and bounded processing.
- Broader acceptance tests across accounts, organizations, retries, restarts, and releases.
- Operational monitoring, recovery procedures, and clearer failure reporting.
- Complete documented model-fidelity and identification-quality evaluation.
- Revisit retention, data/model permissions, and operating costs before expanding use.

## Optional follow-ups

- Replace the CloudFront hostname with a custom domain.
- Refine review and comparison workflows based on field feedback.
- Improve model quality and performance after measuring the current pipeline.

Multiple permission roles, public self-signup, and a large multi-tenant platform are outside the current scope. No infrastructure upgrade or paid account conversion is implied by this roadmap.

See the [README](README.md) for setup, the [original tracer plan](TRACER_BULLET_PLAN.md) for historical scope, and [deployment notes](https://github.com/minghuig/bear-facial-id-app/blob/codex/mvp-accounts/docs/MVP_IMPLEMENTATION.md) for the hosted release.
