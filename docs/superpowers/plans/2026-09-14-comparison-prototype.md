# Unified comparison prototype implementation plan

Goal: Evaluate the approved single flow for comparing known identities and unassigned sightings before explicit assignment.
Architecture: Separate comparison.html React entry with private static photo fixtures. UI state and assignment validation are local, with no backend requests. Existing application stays intact.
Tech stack: Existing React 19, TypeScript, Vite; native Node test runner for pure assignment logic.
Spec: User-approved conversation design: pinned current photo, up to three mixed candidates, complete galleries, draft existing/new bear destination, individually selected unassigned sightings, final review, no implicit identity merging.

## Constraints
- Separate codex/comparison-prototype worktree.
- Real private photos remain ignored; use demo record labels, no model scores or inferred identity claims.
- Assignment simulated only in browser memory; reset restores initial data.

## Tasks
- [x] Test draft logic before implementation: reject existing-bear members being added; include current sighting exactly once; reject missing destinations; existing and new identity payloads; comparison remains separate from assignment.
- [x] Implement model.ts with Photo, Candidate, Draft types and buildAssignment(current, selected, destination, candidates), returning explicit existing/new assignment. Node --experimental-strip-types --test tests/comparison.test.ts verifies behavior.
- [x] Implement fixtures and comparison.html entry. Generate bounded private JPEG assets from local test dataset; document recreation.
- [x] Implement Comparison.tsx: candidate tray/search; pinned query; independent reference galleries; add/remove up to three candidates; zoom dialog; all-photo contact sheet; selected unassigned sightings; destination picker; exact final review; local confirmation, undo, keep-unassigned and reset.
- [x] Implement comparison.css responsive grid, readable photos, horizontal thumbnails, fixed draft footer, accessible dialogs/focus and mobile stacking.
- [x] Run Node tests and npm run build. Browser-evaluate existing identity assignment, five-unassigned grouping, three candidate columns, full gallery, zoom, uncertain exclusions, reset, and narrow viewport.
- [x] Record evidence, commit prototype branch, leave dedicated Vite preview running and open for user evaluation. No merge or release.
