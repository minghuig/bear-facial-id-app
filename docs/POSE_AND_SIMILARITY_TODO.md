# Similarity evaluation and optional pose-quality work

Status: design and offline evaluation only. Do not choose a production identity threshold or present raw cosine as a probability without measured, held-out evidence. The [roadmap](../ROADMAP.md) puts this work after the planned fresh serverless deployment and McNeil photo curation; pose gating is a separate, lower-priority question.

## What the app shows today

The current value is the cosine dot product between two L2-normalized, 512-dimensional six-year PoseSwin embeddings. It ranges from -1 to 1 and ranks reference sightings. It is **not** a probability, calibrated confidence, or statement that the two photos show the same bear. The earlier `test_on_2020` checkpoint produced a different embedding space; its scores and any thresholds must not be reused with the six-year checkpoint.

Results are photo-level: each row is scored against one reference crop, so several photos of one bear can occupy several top-ten positions. Opening a known-bear row shows its other accepted confirmed photos, but those photos did not produce that row's score. A per-bear maximum would deduplicate results without changing the highest-scoring bear; it would still give bears with more reference photos more chances for an unusually high score.

The product question is not merely “what is the cosine?” It is “when should a reviewer trust the suggested bear, and when might this be a bear absent from the library?” A pairwise same-bear probability, a top-candidate correctness probability, and an unknown-bear decision are different targets. Define the target before fitting or labeling any new number.

## Next: build a trustworthy evaluation set

1. After the planned infrastructure cutover, upload and manually identify the approximately 1,000+ McNeil photos. Confirm usable head crops and distinguish verified identities from uncertain ones. Try a smaller curation batch first to learn whether the review flow needs adjustment.
2. Keep capture dates or encounter groups from original metadata or an evaluation manifest. Split by independent capture event, not random photos, so near-duplicates cannot inflate results. Reserve held-out encounters for the final comparison.
3. Check whether these photos are identical or near-duplicate to images in the 2017–2022 McNeil training material for the six-year checkpoint. Such overlap can help exercise the app, but cannot independently establish how well the model generalizes to new photos.
4. Simulate realistic reference galleries from verified labels: some queries should have their bear represented; others should have their bear deliberately absent. Vary the number of reference photos per bear, since gallery size affects maximum similarity.
5. Reuse stored embeddings to compare the current best-photo method, one best photo per bear, top-k aggregation, normalized bear centroids, and score gaps between leading *distinct bears*. Report top-1/top-5 identity retrieval, wrong-but-strong suggestions, and known-versus-unknown tradeoffs at candidate cutoffs. Record enough examples to inspect failures by lighting, angle, season, and crop quality.
6. If the independent sample supports it, fit and evaluate a versioned calibration for a precisely stated claim such as “the top suggested bear is correct under this gallery policy.” Fit and assess on separate data; report uncertainty and the effect of gallery growth. A monotonic rescaling of cosine alone cannot improve ranking, and a small or biased set cannot justify a precise percentage.

The scoring experiments need no new checkpoint or re-embedding once the photos have embeddings. Select the display and decision policy from the evaluation: clearly labeled raw **embedding similarity**, a genuinely calibrated number, or possibly no number. Do not use “confidence,” a percentage, or qualitative bands for raw cosine. Explain which reference photo or aggregate produced the displayed value, and keep historical suggestion definitions/versioning reproducible.

## Later, only if useful: pose-quality handling

The released PoseSwin code computes mean confidence over 13 HRNet pose heatmaps for the original and flipped crop. Only Bears stores both diagnostics but does not reject an embedding from them. An upstream commented `avg_conf < 0.8` line is an experiment clue, **not** a validated threshold for this app. Crop approval answers whether the crop contains a usable bear head; pose confidence is a different signal and must not be confused with identity confidence.

If the labeled evaluation reveals a real pose-related failure pattern, compare original/flipped means, their minimum, or per-keypoint rules on held-out encounters. Measure how warnings or exclusions change retrieval and false rejections, including difficult but important photos. Prefer a reversible warning to a hard gate unless the evidence strongly supports exclusion. Keep detector acceptance, pose-quality handling, and identity-match decisions as separately named thresholds.

## Done when a change is justified

- A versioned report states the verified dataset, encounter split, gallery policy, metrics, candidate cutoffs, uncertainty, and observed failure cases.
- API/UI score names and tests distinguish raw pairwise cosine from any calibrated or aggregated bear-level value; saved suggestions retain the definition used at the time.
- Any hard exclusion has a visible reviewer recovery path and measured false-reject behavior.
