# Simple comparison prototype

Open http://127.0.0.1:5175/comparison.html in the separate codex/comparison-prototype worktree.

The current sighting stays on the left. Click any similar-sighting thumbnail to change the right side. Named and unnamed bear records expose all their photos directly below the right image, with thumbnails and previous/next controls. Enlarge photos opens the same pair at a larger size. No grouping, assignment, confirmation or saving UI remains.

This is a frontend-only prototype using private field photos and curated matches with synthetic similarity values, sorted highest first. No inference or production mutations. Photos use original framing, not detector crops.

## Running

From frontend, run `npm.cmd run dev -- --port 5175 --strictPort` and open `/comparison.html`.

To recreate ignored local assets using Python with Pillow:

```powershell
python scripts/prepare_comparison.py 'C:/Users/zFlei/repos/bear-facial-id-app/.private/test-data/bear-photos'
```

## Validation

`npm.cmd --prefix frontend run build` builds both the original app entry and this prototype. Browser checks verified the two-photo layout, all seven Cedar references, selecting photo7 then switching to a singleton resets the photo index, enlargement shows the selected pair, and the match strip is ordered by demo similarity. Earlier assignment prototype commits remain in branch history; their plan and helper tests describe the prior design, not the current viewer.
