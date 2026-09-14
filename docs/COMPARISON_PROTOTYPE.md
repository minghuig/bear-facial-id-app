# Comparison prototype

Open http://127.0.0.1:5175/comparison.html.

Branch: codex/comparison-prototype. This is a separate frontend entry; the existing index.html application is retained. All assignments live only in React memory and reset on reload. No API requests, inference, upload, database or deployment integration is included. Candidate names are demo labels; displayed candidates are curated fixtures, not recognition results. Photos show original framing, with enlargement and independent scrolling rather than detector crops.

## Try these flows

1. Compare Cedar and Unnamed bear 07 alongside Sighting B. Click thumbnails, Next/Previous or View all 7 photos. Enlarge the current/reference pair, or compare the candidates with each other. Up to three candidate columns are supported. On narrow screens panels stack.
2. Select B, C, D and E in the top Select photos to identify together section; choose New unnamed bear and Review & confirm. Inspect all five photographs. Remove D if uncertain, then simulate creation: A/B/C/E appear in Unnamed bear 08, while D stays separate.
3. Reset demo. Choose Choose Cedar (or select any existing bear in the destination menu), optionally include unassigned sightings, then Review & confirm. All seven existing photos appear alongside exactly the additions. Simulation adds those photos only to that record.
4. Undo an assignment even after dismissing its notice. Keep unassigned records a visible simulated review without assigning an identity. Reset demo restores all fixtures and clears search/filter/draft.

## Run or recreate

From frontend:

```powershell
npm.cmd ci --offline --ignore-scripts
npm.cmd run dev -- --port 5175 --strictPort
```

Then open /comparison.html. npm run build outputs both index.html and comparison.html.

Photos are private and excluded by /frontend/public/demo-photos/ in .gitignore. A fresh worktree needs local photo preparation using Python with Pillow:

```powershell
python scripts/prepare_comparison.py 'C:/Users/zFlei/repos/bear-facial-id-app/.private/test-data/bear-photos'
```

The script reads battle, cc, goucho and blond_anteater folders, emits JPEGs bounded to 1600 pixels under frontend/public/demo-photos, and updates frontend/src/comparison/photos.json. Originals remain unchanged. The main checkout's user-provided photos are the source. No assets are uploaded or checked into Git.

## Validation

```powershell
cd frontend
node --experimental-strip-types --test tests/comparison.test.ts
npm.cmd run build
```

Five model tests cover selected unassigned IDs, duplicate elimination, prevention of existing-identity merging, valid destinations, and descending nonmutating similarity ranking. They were observed failing before implementation, then passing.

Browser QA on the dedicated local preview verified:
- All seven Cedar photos in complete gallery; choosing photo 7 updates the comparison.
- Existing assignment final review shows seven references plus current A; simulated save yields eight Cedar photos.
- Select appended photo 8, dismiss save notice, undo and enlarge candidate comparison: no crash, seven-photo gallery restored.
- Five unassigned sightings appear in new-record review; nested photo inspection works; removing D yields four-photo unnamed record, D remains unassigned.
- Three mixed candidate columns; attempted fourth produces explicit limit feedback.
- Enlargement and 200% zoom; complete gallery and confirmation dialogs; keep-unassigned notice.
- Desktop 1280x720 and mobile 390x844 screenshots inspected. Mobile panels stack; draft controls stay reachable. Viewport override reset.
- No console warnings/errors captured during these flows.

Independent code review identified stale indices after undo and a dismissible undo control. Both were fixed and the exact browser regression was exercised. Prototype quality does not establish model accuracy or production assignment durability.

## Compact revision

The selection strip and Identify as / Review & confirm controls now lead the page, followed immediately by similarity-ranked candidates and compact comparison panels. Candidate actions say Choose [bear] and Add this photo to selection. The old enlarged-candidate button is removed; clicking images opens inspection, and Full screen expands the whole current comparison. Demo scores are synthetic cosine-style values, clearly labeled, descending; they are not model results or identity probabilities.

Revised browser QA: at the default 1252x873 viewport, the selection block ends at y224; all three comparison candidates and their controls fit on the page. A+B with Choose Cedar still yields seven existing references plus exactly two additions in final review. Full screen contains current A and all three selected candidates. Sorting observed B .936, C .912, E .887, Unnamed07 .834, D .821, Cedar .786, Willow .744. Temporary viewport override was reset. Initial JSX punctuation error during editing was fixed; subsequent TypeScript/Vite build passed. Independent follow-up review found no actionable regressions.
