# Real inference validation and private artifacts

This historical model-fidelity regression runs only on approved AWS x86_64 compute with an IMDSv2 identity, while the ordinary local CPU development stack also supports real inference inside Linux Docker containers. Local packaging reads bytes and hashes; it does not import ML libraries or execute checkpoints. The AWS regression is required before claiming deployed real inference validation and is separate from the application workflow acceptance test.

## Package locally

From the repository root:

```sh
python3 scripts/package_artifacts.py
```

The command packages the four trusted checkpoints, 12 pilot originals, 35 manually cropped field heads, their original manifests, saved head-detector results, and saved **six-year-model field embeddings** into `.private/`. The head/pose checkpoints and images come from `bear-id`; the verified six-year ReID checkpoint and field embeddings come from `.private/checkpoint-candidates/` in this workspace. The public MegaDetector checkpoint must already be in `.private/models/` (run `make body-model`). It checks checkpoint hashes against `workers/trusted.py` and images against prototype manifests before copying. Reports/manifests without previously recorded trusted hashes receive transfer-integrity hashes, not a new authenticity claim. Existing different destination bytes cause failure. Source labels and notes are copied verbatim as evaluation metadata and never imported as confirmations. The prototype is never modified or relocated.

`.private/package-manifest.json` records every destination, SHA-256, and size. `.private/` is Git ignored and excluded by `.dockerignore`. Keep this directory and output reports out of source control, container images, logs, and public storage. Transfer it only to the approved private S3 prefix/EC2 storage using the infrastructure runbook. No transfer or paid benchmark is authorized by packaging alone.

## Run on AWS after spending approval

Use the images built from the exact released commit, and record that commit. Run the three containers sequentially to measure the actual placement without simultaneous model memory pressure. The following commands execute **on the AWS host**, with the private package at `/opt/only-bears/private`. Adapt only the directory and image tags to the deployment output.

```sh
sudo install -d -m 0770 -o 10001 -g 10001 /opt/only-bears/private-reports
sudo chown -R 10001:10001 /opt/only-bears/private
sudo chmod 700 /opt/only-bears/private
export RELEASE_COMMIT='<exact released commit>'
export BODY_DETECTOR_IMAGE='<versioned body-detector image>'
export HEAD_DETECTOR_IMAGE='<versioned detector image>'
export RECOGNITION_IMAGE='<versioned recognition image>'
sudo docker run --rm --network host -e RELEASE_COMMIT="$RELEASE_COMMIT" \
  -v /opt/only-bears/private:/private:ro \
  -v /opt/only-bears/private-reports:/reports \
  "$BODY_DETECTOR_IMAGE" python validate.py body_detection --output /reports/body-detection.json
sudo docker run --rm --network host -e RELEASE_COMMIT="$RELEASE_COMMIT" \
  -v /opt/only-bears/private:/private:ro \
  -v /opt/only-bears/private-reports:/reports \
  "$HEAD_DETECTOR_IMAGE" python validate.py head_detection --output /reports/head-detection.json
sudo docker run --rm --network host -e RELEASE_COMMIT="$RELEASE_COMMIT" \
  -v /opt/only-bears/private:/private:ro \
  -v /opt/only-bears/private-reports:/reports \
  "$RECOGNITION_IMAGE" python validate.py recognition --output /reports/recognition.json
```

The runner requires Linux x86_64 and an EC2 IMDSv2 identity response **before importing ML**. Host networking lets the container use IMDS when the metadata hop limit is one; it publishes no service. Do not add a bypass for local testing. If metadata access is blocked, diagnose AWS host metadata configuration rather than disabling the guard.

Each checkpoint is hash checked at loading, and all private transfer files are checked before inference. The body run verifies the frozen graph loads and emits finite, valid MegaDetector records above 0.90 on all 12 inputs; there is not yet a saved body-output fidelity fixture. Head detection requires 12 rows with matching oriented dimensions and detection counts; coordinates must differ by at most one pixel and scores by at most 0.001, with exact counts at the 0.5 acceptance threshold. Results retain all returned boxes for inspection. Recognition requires 35 finite normalized 512-element outputs, each with cosine >= 0.999 against its corresponding saved field embedding. A mismatch fails the command, records the evidence, and must be investigated rather than weakening thresholds silently.

Reports persist after each image and on errors. They include package versions, release commit, instance type, region, per-image duration (first image includes cold model loading), total duration, Linux peak process RSS, and available cgroup peak/limit measurements. Peak process RSS is not total host memory. Record remote image build time, container image sizes, host memory, startup overhead, and any OOM separately in the deployment progress record before settling worker placement. Private reports contain detections and should stay private; public progress may summarize counts, timings, and memory.

## Provenance and scope

The ReID implementation derives from the [BrownBear_ReID repository](https://github.com/amathislab/BrownBear_ReID) and the associated paper, [“Individual identification of brown bears using pose-aware metric learning”](https://doi.org/10.1016/j.cub.2025.12.022), by Beth Rosenberg, Mu Zhou, Nathan Wolf, Mackenzie Weygandt Mathis, Bradley P. Harris, and Alexander Mathis. The pinned upstream source commit is `4a9f5be8a57c7493096cab1b114dcd71489a3dbe`; see [`ACKNOWLEDGMENTS.md`](../ACKNOWLEDGMENTS.md), `workers/vendor/NOTICE`, and `SOURCE_HASHES.json` for full credit and provenance. The ReID adapter uses the released `katmai_exps/6y_model/net_best.pth` checkpoint, trained on all six McNeil years for the paper's Katmai cross-site experiment. It preserves a separate HRNet pose model, V1 Swin width 128, 512-dimensional features, RGB resize to 224×224, ImageNet normalization, original plus horizontal flip summation and L2 normalization. The training classifier's 109 outputs do not define application identities. Five-year `test_on_2020` vectors remain a separate historical embedding space and must never be compared with the six-year vectors.

Body detection uses MegaDetector v4.1 at strict `confidence > 0.90`. The API expands each body box by 3% of the original image dimensions when each margin fits, matching the released BrownBear preprocessing edge behavior, and saves a JPEG body crop. Head detection uses the checkpoint-embedded legacy MMDetection config, strict loading, BGR input, and CPU execution in its own Python 3.9 image; it runs on those body crops at threshold 0.5. A person must approve each resulting head crop before recognition. Recognition uses its own newer environment. Checkpoint and upstream licensing questions recorded in the prototype remain unresolved for any future staff rollout.

Passing these regressions establishes extraction fidelity, not identification quality or full tracer-bullet completion. The deployed upload → body detection → head detection → durable crop-curation pause → recognition → confirmation → later-photo retrieval workflow, retries and persistence across restart/release must also be demonstrated. Never promote saved expected labels or predictions into human-confirmed gallery references.
