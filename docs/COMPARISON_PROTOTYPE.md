# Full photos-to-comparison prototype

Open http://127.0.0.1:5175/comparison.html. It now starts at Photos & review with the main-branch photo-library component (copied into comparison/library for isolation), search/status/bear filters, pagination, a selected photo and sighting review panel.

## Walkthrough

1. Choose IMG_2022.JPG or another unassigned photo in the library.
2. Click Compare matches, or a specific suggested match in the review panel.
3. Inspect the current photo and one matching sighting; browse all available reference photos of established bear records.
4. Confirm same bear, then Yes, same bear. The prototype links exactly the two unidentified sightings, or adds the current sighting to the chosen existing record.
5. Return to photo. Its identity and library status now reflect the decision. The library's filters and selected photo persist across navigation.
6. Undo confirmation restores the previous collection and returns to the library. Keep unidentified saves a simulated review without assigning identity. Reset demo restores the initial collection.

The page uses 26 private local photo fixtures, curated demo candidates and synthetic scores. This is not production inference. All edits are browser-memory-only and reload resets the collection. The prototype starts after upload/recognition with one sighting per photo; it does not implement upload, multi-head detection, durable saving, browser history routing or production API integration. Existing main/index.html stays unchanged in the worktree. Prior prototype designs remain in Git history.

## Running

From frontend: `npm.cmd run dev -- --port 5175 --strictPort`. Open `/comparison.html`.

To recreate ignored JPEG assets using Python with Pillow:

```powershell
python scripts/prepare_comparison.py 'C:/Users/zFlei/repos/bear-facial-id-app/.private/test-data/bear-photos'
```

## Verification

- `node --experimental-strip-types --test frontend/tests/comparison.test.ts frontend/tests/journey.test.ts`: seven tests pass, including exact two-sighting grouping and immutable existing-bear addition.
- `npm.cmd --prefix frontend run build`: TypeScript and both Vite entry points.
- Browser: library screenshot inspected, search2022 -> compare -> unknown confirmation -> return retains filter and selected photo; linked2090 reflects same new bear; current photo excluded from its own reference gallery; named Cedar confirmation returns updated status; lower-ranked C opens selected without changing similarity order; new identity reopen/undo returns safe library; old stale-record crash no longer reachable.
- Independent review identified stale snapshot after undo and reordered similarity strip. Both fixed and exact browser paths verified.

Source is retained only on codex/comparison-prototype. No merge/deployment/production writes.

## Live integration

The main app now opens the same simple comparison flow using live recognition candidates. Eligible unidentified sightings appear alongside known identities, ordered by similarity; each known candidate exposes its full confirmed gallery. Confirmation writes a reviewed identity. Change identity moves only the current sighting, with guarded Undo based on saved review history. All access retains the deployed organization and sign-in boundaries. Demo comparison.html remains a local Vite prototype and is excluded from the production build.

BEAR-32: successful confirmation returns automatically to the photo library, preserving selection and filters, with Undo bound to the saved sighting. Failed saves and cancellation stay in comparison. The main review panel lists live similar sightings vertically with similarity scores; each Compare button opens that candidate.
