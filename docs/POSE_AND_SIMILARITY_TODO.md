# TODO: pose-quality gating and similarity semantics

Status: design and evaluation work only. Do not choose a production threshold or relabel the score without measured evidence.

## Why this is separate from the body-to-head crop change

The released PoseSwin code computes the mean confidence of the 13 HRNet pose heatmaps for both the original and flipped crop. It returns those values in Only Bears diagnostics, but neither the released research code nor the app currently rejects an embedding based on them. The upstream source contains a commented `avg_conf < 0.8` line; that is a clue about an experiment, not a specified or validated operating threshold.

The body → padded body crop → head detector → manually approved head crop pipeline can therefore ship independently. Pose gating should follow only after evaluating real app inputs, because a poor threshold could discard useful sightings or give reviewers unjustified confidence.

## Decisions the design must make

1. Define the unit being gated: original-pose mean, flipped-pose mean, their minimum, their mean, or a per-keypoint rule.
2. Define the action: warn, sort lower, require an extra review, exclude from the gallery, or skip recognition. A soft warning should be the default candidate until the data supports a hard rejection.
3. Choose candidate thresholds from measured distributions. Include `0.8` as an upstream-inspired candidate, not a default.
4. Keep crop approval and pose quality distinct. Crop approval answers “is this actually a usable bear-head crop?”; pose quality estimates whether HRNet found a stable pose signal.
5. Store the metric definition and threshold version with every recognition result so later comparisons are reproducible.

## Evaluation needed before choosing a threshold

- Build a review set of accepted and rejected crops spanning cameras, lighting, blur, occlusion, head angles, seasons, and known repeated bears.
- Preserve encounter or capture-event separation between evaluation pairs to avoid near-duplicate leakage.
- For each crop, record `pose_original`, `pose_flipped`, keypoint confidences if exposed, recognition rank, cosine values, and the human crop/identity outcome.
- Measure coverage versus retrieval quality at several thresholds. At minimum report top-1/top-5 retrieval, false-match rate, false-reject rate, and the share of uploads sent to manual review or excluded.
- Check performance separately for underrepresented conditions; a globally better threshold can still systematically reject difficult but important sightings.
- Select a threshold only if it improves the agreed operational metric on held-out data. Otherwise retain diagnostics and warnings without gating.

## What “similarity” means today

The current value is the cosine dot product between two L2-normalized, 512-dimensional PoseSwin embeddings. It ranges from -1 to 1 and is used to rank reference sightings. It is not a probability, calibrated confidence, or statement that two photos show the same bear.

The released six-year checkpoint uses a different embedding space from `test_on_2020`. Similarity values and any future decision thresholds must be evaluated afresh for that model; legacy and new scores should not be compared as if they shared a calibrated scale.

Results are currently photo-level: each candidate row is scored against one specific reference crop, so several photos assigned to the same bear can occupy several top-10 positions. Opening a known-bear candidate shows the rest of that bear’s accepted confirmed gallery, but those extra photos did not produce that row’s displayed score.

## Product questions to resolve

- Decide whether the product should rank photos, bears, or both. If ranking bears, compare max similarity, top-k aggregation, a centroid/prototype, or a learned/set-based method on held-out encounters.
- Rename the UI value to **embedding similarity** unless and until calibration supports another term. Never call raw cosine “confidence” or display it as a percentage.
- Decide whether users benefit from the number at all. Candidate order plus qualitative bands may be more honest, but bands also require calibration.
- If a number remains visible, add an inline explanation of what two crops generated it and keep sufficient precision for reproducibility without implying certainty.
- Separate three thresholds: detector acceptance, pose-quality handling, and identity-match decision support. They measure different things and must not share a label.
- Define how a newly confirmed photo changes an existing bear candidate and how to explain multiple supporting photos.

## Acceptance criteria for future implementation

- A versioned evaluation report identifies the dataset split, metric definitions, candidate thresholds, chosen policy, uncertainty, and subgroup checks.
- API fields name raw cosine explicitly or expose a separately calibrated value with its calibration version.
- UI copy and tests make clear whether a candidate represents a crop or an aggregated bear.
- Historical suggestion snapshots retain the score definition/version used when they were created.
- Any hard pose gate has a visible recovery path and is covered by false-reject monitoring.
