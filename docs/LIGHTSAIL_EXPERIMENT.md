# Lightsail and cheaper EC2 experiment

Local experiment, September 14, 2026. Production remains on the existing EC2. No cloud resources were created, resized, stopped, or upgraded.

## Recommendation

A **4 GB x86 Lightsail server ($24/month)** is a plausible later migration, pending an actual host test and an authenticated ingress/credential design. The local real models fit with a 768 MiB service reserve. This is not evidence of Lightsail CPU speed, sustained throughput, or whole-app reliability. Keep EC2 for the current release.

A 2 GB EC2 `t3.small` is the cheapest tested-memory x86 candidate marked Free Tier eligible, but its memory margin is narrow; do not resize production based on this small probe. If recognition is moved elsewhere, 2 GB becomes a more comfortable portal/database candidate.

## What was tested

Reproduction (PowerShell, Docker Desktop running):

```powershell
./experiments/lightsail/run.ps1 -Models 'C:/path/to/checkpoints' -Prototype 'C:/path/to/private-bear-id'
```

The script expects the existing `only-bears-local-cpu-detector` and `only-bears-local-cpu-recognition` images. Build missing images with `docker build -f workers/Dockerfile.detector -t only-bears-local-cpu-detector .` and the corresponding recognition Dockerfile/tag. Source workers are mounted from this branch, so installed dependencies come from the image but model code comes from this checkout.

Each stage receives two CPU equivalents, either 4 or 2 GiB RAM, **no swap**, and no network. A touched 768 MiB allocation stays resident to reserve space for the OS, Docker, API, Postgres, Caddy and idle worker supervisors. That reserve is an estimate, not a running full stack. Existing local containers were left alone. All three checkpoint hashes are verified by the real worker loader.

Inputs: original pilot `p002.jpg` (4618x3464) and `p012.jpg` (5184x3888); field crops `q001.jpg`, `q002.jpg`, `q003.jpg`. Inference uses production `detector.boxes` and `recognition.embed` directly, bypassing HTTP, job queues, database writes and crop generation. Detector returned one and two boxes respectively. Recognition validates 512 finite, unit-normalized embedding values. Input hashes, image IDs, timings and memory counters are in `experiments/lightsail/results/`.

The first image of each container includes model import/load and checkpoint hashing; later images reuse that model. Production reloads models per job, so **cold timings are the useful planning figures**, not warm per-image throughput. Recognition may process several heads within one job. A fresh process does not imply cold host disk/page caches. Windows bind mounts and other running containers affect timings.

Memory is Linux cgroup v2 `memory.peak` (charged memory including the reserve and charged file cache); process RSS is `getrusage(RUSAGE_SELF).ru_maxrss`. Shared/file-backed accounting differs, so RSS and cgroup peaks are not interchangeable. Docker inspect independently records exit code and OOMKilled. Peak numbers include the 768 MiB reserve; do not add it again.

| RAM limit | Stage | Cold first image | Warm following images | Cgroup peak incl. reserve | Result |
|---|---|---:|---:|---:|---|
| 4 GiB | Detection | 49.24 s | 11.70 s | 1849 MiB | pass |
| 4 GiB | Recognition | 37.46 s | 3.70 / 4.53 s | 2029 MiB | pass |
| 2 GiB | Detection | 45.61 s | 12.31 s | 1706 MiB | pass |
| 2 GiB | Recognition | 43.67 s | 4.07 / 4.60 s | 2029 MiB | pass, marginal |

All four containers exited zero with no recorded OOM events. The 2 GiB recognition peak leaves only **19 MiB** within the test budget. Real concurrent uploads, database growth or larger crops can exhaust that margin. **2 GiB is not approved as a whole-stack production size.** 4 GiB leaves about 2 GiB beyond this measured peak, making it the stronger next test. No workload throughput or recognition-accuracy conclusion follows from these five inputs.

## Monthly prices before credits

Ohio Linux on-demand, 730 running hours, September 14. EC2 totals add **50 GB gp3 ($4) + one public IPv4 ($3.65)**. Lightsail includes its disk and public IPv4. All totals exclude shared S3, ECR, logs, taxes and any overage; allow roughly $3-6 extra for current small storage, depending on image retention and traffic. Exact billing will vary.

| Candidate | RAM | Compute/bundle | EC2 plus disk/IP | FreeTierEligible API |
|---|---:|---:|---:|---|
| Current m7i-flex.large | 8 GB | $69.90 | $77.55 | yes |
| c7i-flex.large | 4 GB | $61.90 | $69.55 | yes |
| t3.small | 2 GB | $15.18 | $22.83 | yes |
| t3.medium | 4 GB | $30.37 | $38.02 | no |
| t3.large | 8 GB | $60.74 | $68.39 | no |
| t3a.small | 2 GB | $13.72 | $21.37 | no |
| t3a.medium | 4 GB | $27.45 | $35.10 | no |
| t3a.large | 8 GB | $54.90 | $62.55 | no |
| t4g.small (ARM) | 2 GB | $12.26 | $19.91 | yes |
| t4g.medium (ARM) | 4 GB | $24.53 | $32.18 | no |
| t4g.large (ARM) | 8 GB | $49.06 | $56.71 | no |
| Lightsail small_3_0 | 2 GB | $12 | included | creation unverified |
| Lightsail medium_3_0 | 4 GB | $24 | included | creation unverified |
| Lightsail large_3_0 | 8 GB | $44 | included | creation unverified |

Prices checked through AWS Pricing/GetBundles by the coordinating task; EC2 eligibility independently checked here with `describe-instance-types`. This account is currently on the FREE plan. Catalogue and empty `lightsail get-instances` queries succeeded; that **does not prove instance creation is allowed**. The advertised 90-day Lightsail trial specifically says Paid plan and only includes Linux IPv4 bundles up to $12, not the $24 bundle. Do not upgrade or assume this trial/credit coverage without owner approval. FreeTierEligible is AWS eligibility metadata, not unlimited free runtime. Noneligible EC2 rows are future paid-plan comparisons.

ARM is not a drop-in saving: both model Dockerfiles specify linux/amd64 and the old MMDetection/MMCV wheel is x86. An ARM dependency build and inference equivalence test would be needed; emulation is not a validated production plan.

Bursty pricing matters: t3/t3a medium sustain 20% per vCPU (0.4 CPU total), large 30% (0.6 CPU total). Two-CPU local runs approximate available burst capacity, not exhausted-credit performance. Standard mode throttles after credits; Unlimited can charge $0.05 per surplus vCPU-hour for Linux T3/T3a ($0.04 for T4g). Lightsail also has burst limits. Long batches need a real sustained test. **Lightsail continues billing while stopped** until deleted, whereas EC2 compute stops billing when stopped (disk and possibly retained addresses remain billed). Intermittent current EC2 use can be cheaper than a fixed monthly migration.

## Migration work before any switch

1. Retain Docker Compose, Postgres and sequential inference; keep model subprocess unloading. Package frontend/auth and use the reviewed organization boundary from the MVP branch, not this experiment's older main baseline. Transfer the database and reconcile S3 references in a deliberate cutover.
2. Replace EC2-specific Terraform/release paths, instance metadata, SSM deployment, awslogs and ECR/S3 credential assumptions. A Lightsail service-linked role is not an application EC2 instance profile. Prefer a reviewed short-lived credential/deployment solution; do not copy an administrator profile onto the host.
3. Redesign ingress: the planned CloudFront **private EC2 VPC origin cannot simply target Lightsail**. Keep Google authentication and private S3. A public HTTPS origin would require valid origin TLS, a secret origin header enforced by the reverse proxy, restricted exposed routes, and disabled caching for auth/API. The CloudFront browser address and Google redirect can remain, but origin TLS still needs solving. Do not expose the API or Postgres directly.
4. After explicit provisioning/cost approval, run one real 4 GB host smoke test with the authenticated full stack, serial model jobs and representative uploads; measure free memory, burst depletion and latency. Preserve EC2 rollback until success. This branch makes no infrastructure changes.

## Sources

- [Lightsail bundles](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html) and [trial eligibility](https://aws.amazon.com/free/compute/lightsail/)
- [EC2 on-demand and surplus CPU pricing](https://aws.amazon.com/ec2/pricing/on-demand/) and [CPU credit baselines](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/burstable-credits-baseline-concepts.html)
- [Lightsail burst capacity](https://docs.aws.amazon.com/lightsail/latest/userguide/cpu-burst-capacity-accrual.html) and [stopped-instance billing](https://repost.aws/knowledge-center/lightsail-billing)
- [CloudFront VPC origins](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-vpc-origins.html) and [Lightsail distribution origin configuration](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-creating-content-delivery-network-distribution.html)
