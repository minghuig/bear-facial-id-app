import photos from './photos.json';
import type { Candidate, Photo } from './model';
export const current: Photo = {...photos.battle[0],id:'a',label:'Sighting A'};
export const initialCandidates: Candidate[] = [
  {id:'cedar',label:'Cedar',kind:'bear',photos:photos.cc,similarity:.786},
  {id:'unnamed-07',label:'Unknown bear 07',kind:'bear',photos:photos.goucho,similarity:.834},
  ...photos.battle.slice(1,5).map((p,i)=>({id:String.fromCharCode(98+i),label:`Sighting ${String.fromCharCode(66+i)}`,kind:'sighting' as const,photos:[p],similarity:[.936,.912,.821,.887][i]})),
  {id:'willow',label:'Willow',kind:'bear',photos:photos.blond_anteater,similarity:.744},
];
