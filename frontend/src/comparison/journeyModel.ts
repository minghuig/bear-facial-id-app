import type { Candidate, Photo } from './model';
export type Collection = { records: Candidate[]; links: Record<string,string> };
export function confirmSighting(state:Collection, current:Photo, match:Candidate):Collection {
 if(state.links[current.id])throw new Error('Sighting already assigned');
 const target=match.kind==='bear'?match.id:state.links[match.photos[0].id];
 if(target){
  if(!state.records.some(r=>r.id===target))throw new Error('Bear record missing');
  return {records:state.records.map(r=>r.id===target?{...r,photos:[...r.photos,current]}:r),links:{...state.links,[current.id]:target}};
 }
 const id=`unnamed-${current.id}-${match.id}`;
 return {records:[...state.records,{id,label:`Unnamed bear ${state.records.length+1}`,kind:'bear',photos:[current,match.photos[0]]}],links:{...state.links,[current.id]:id,[match.photos[0].id]:id}};
}
