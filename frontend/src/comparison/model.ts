export type Photo = { id: string; src: string; label: string };
export type Candidate = { id: string; label: string; kind: 'bear' | 'sighting'; photos: Photo[] };
export function buildAssignment(current: string, selected: string[], destination: string, candidates: Candidate[]): {destination:string;sightingIds:string[]} {
  if (destination !== 'new' && !candidates.some(c=>c.id===destination && c.kind==='bear')) throw new Error('Choose a bear destination');
  const sightingIds = [...new Set([current, ...selected])];
  if (sightingIds.some(id=>id!==current && !candidates.some(c=>c.id===id && c.kind==='sighting'))) throw new Error('Only unassigned sightings can be added');
  return {destination,sightingIds};
}
