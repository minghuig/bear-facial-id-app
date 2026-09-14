# Simple comparison prototype

Open http://127.0.0.1:5175/comparison.html in the separate codex/comparison-prototype worktree.

The current sighting stays on the left. Click any similar-sighting thumbnail to change the right side. Named and unnamed bear records expose all their photos directly below the right image, with thumbnails and previous/next controls. Confirm same bear appears beneath the match. A short confirmation explains either linking the two unassigned sightings or adding the current sighting to an existing bear. Saving is simulated, with Undo; further confirmation is disabled until undo. Enlargement has been removed.

This is a frontend-only prototype using private field photos and curated matches with synthetic similarity values, sorted highest first. No inference or production mutations. Photos use original framing, not detector crops.

## Running

From frontend, run `npm.cmd run dev -- --port 5175 --strictPort` and open `/comparison.html`.

To recreate ignored local assets using Python with Pillow:

```powershell
python scripts/prepare_comparison.py 'C:/Users/zFlei/repos/bear-facial-id-app/.private/test-data/bear-photos'
```

## Validation

`npm.cmd --prefix frontend run build` builds both the original app entry and this prototype. Browser checks verified the two-photo layout, all seven Cedar references, selecting photo7 then switching to a singleton resets the photo index, enlargement shows the selected pair, and the match strip is ordered by demo similarity. Earlier assignment prototype commits remain in branch history; their plan and helper tests describe the prior design, not the current viewer.

Confirmation revision: five model tests and frontend build pass. Browser checked both unassigned and existing Cedar confirmations, exact consequence text, success feedback and Undo. The model assignment helper validates the selected target. No photo gallery/database mutation occurs; this prototype simulates confirmation feedback only.
