# Roadmap

Only Bears is a hobby app for a small invited group. The priority is a usable photo-review flow and similarity information people can interpret, not a larger feature set or production-grade availability. This is a direction and status guide, not a delivery schedule or authorization to change AWS resources.

## Current state

The hosted app supports uploads, body-to-head detection, manual head-crop review, six-year PoseSwin recognition, comparison with similar sightings, human identity confirmation/correction, photo and bear deletion, search and filters, and separate invited-account libraries. Local real-CPU development and a mock test stack are available. See the [README](README.md) for the current workflow and setup.

The displayed similarity is still a **raw cosine score for a pair of head crops**. Results are ranked by reference photo, so one bear can appear multiple times. The score is not a probability that the suggested bear is correct. The current EC2 deployment remains in use; ordinary releases preserve its database and photos.

## Next: decide and execute the serverless migration

The selected direction is a web/API Lambda, on-demand Fargate inference tasks, and Aurora Serverless v2 PostgreSQL, retaining the existing CloudFront entry point where practical. This is **planned, not implemented or scheduled**. Follow the staged tests, cost checks, approval gates, and cutover procedure in the [serverless migration plan](docs/SERVERLESS_MIGRATION_PLAN.md); if the measured complexity or savings do not justify it, reconsider staying on EC2.

The current plan deliberately starts the new deployment with an **empty database and fresh photo storage**. It does not transfer prototype photos, bear IDs, reviews, or embeddings. Do not spend time identifying the full McNeil collection in the current app and silently lose that work at cutover. Either wait until after migration to do the large curation pass, or explicitly revise the migration plan to preserve/import the data first. The reset is a planning choice, not an inherent requirement of serverless infrastructure.

## After cutover: curate McNeil photos and make similarity meaningful

- Upload and manually identify the approximately 1,000+ McNeil photos, confirming usable head crops and recording uncertain identities as uncertain. First try a smaller batch to find any real friction in the upload/review flow before committing to the whole collection.
- Keep capture dates or encounter groupings from the original photos (or a small evaluation manifest) so near-duplicates do not appear on both sides of a test. Check whether any photos overlap the 2017–2022 McNeil images used to train the [six-year checkpoint](docs/INFERENCE.md); overlapping images cannot serve as an independent test of generalization.
- Build a reproducible **offline** evaluation from verified identities and existing embeddings. Include both bears present in the reference library and deliberately held-out bears absent from it. Compare current best-photo cosine with alternatives such as best-per-bear, top-k photo aggregation, bear centroids, and the gap between leading candidates. Report ranking quality and wrong-but-strong suggestions, not just average similarity.
- Decide what question the product's number should answer. Keep raw embedding similarity clearly labeled unless held-out data supports a calibrated statement such as the likelihood that the top suggested bear is correct. Choose any decision threshold and UI wording from that evaluation, not from an arbitrary cosine value. See the [similarity design TODO](docs/POSE_AND_SIMILARITY_TODO.md).

Once uploads have generated embeddings, scoring and display experiments can reuse them; they do not require another checkpoint, photo re-upload, or re-embedding. A thousand photos will help only to the extent that they cover trustworthy identities and independent encounters.

## Small cleanup, as needed

- Complete real invited-user sign-in and organization-switching checks if still outstanding; the [deployment notes](docs/MVP_IMPLEMENTATION.md) record these as needing owner browser verification.
- Keep the README, deployment instructions, and historical plans clearly labeled as the architecture changes. Remove stale roadmap items rather than carrying completed MVP work forward.
- Before the full curation pass, arrange a modest backup or export of photo-to-bear decisions and original photos. This protects the owner's labeling work without becoming a broad reliability program.
- Refine upload/review ergonomics only where the smaller curation batch exposes actual friction. Defer pose-quality gating until evidence shows it helps; keep it distinct from identity-score calibration.

Custom domains, more permission roles, public sign-up, and general platform hardening are not current priorities. See the [original tracer plan](TRACER_BULLET_PLAN.md) and [deployment notes](docs/MVP_IMPLEMENTATION.md) for historical scope and release details.
