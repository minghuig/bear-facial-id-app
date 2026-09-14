import photos from './photos.json';
import type { Candidate, Photo } from './model';
export const current: Photo = {...photos.battle[0],id:'a',label:'Sighting A'};
export const initialCandidates: Candidate[] = [
  {id:'cedar',label:'Cedar',kind:'bear',photos:photos.cc},
  {id:'unnamed-07',label:'Unnamed bear 07',kind:'bear',photos:photos.goucho},
  ...photos.battle.slice(1,5).map((p,i)=>({id:String.fromCharCode(98+i),label:`Sighting ${String.fromCharCode(66+i)}`,kind:'sighting' as const,photos:[p]})),
  {id:'willow',label:'Willow',kind:'bear',photos:photos.blond_anteater},
];
