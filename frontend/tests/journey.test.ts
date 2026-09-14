import { test } from 'node:test';
import { strict as assert } from 'node:assert';
import { confirmSighting } from '../src/comparison/journeyModel.ts';
const a={id:'a',src:'a',label:'A'},b={id:'b',src:'b',label:'B'};
const state={records:[{id:'known',label:'Cedar',kind:'bear' as const,photos:[{id:'k',src:'k',label:'K'}]}],links:{k:'known'}};
test('existing bear receives current sighting without changing other records or original state',()=>{
 const next=confirmSighting(state,a,state.records[0]);
 assert.equal(next.links.a,'known');assert.equal(next.records[0].photos.length,2);assert.equal(state.records[0].photos.length,1);
});
test('unidentified comparison creates one record for exactly the two selected sightings',()=>{
 const next=confirmSighting(state,a,{id:'b',label:'B',kind:'sighting',photos:[b]});
 assert.equal(next.links.a,next.links.b);assert.deepEqual(next.records.at(-1).photos.map(p=>p.id),['a','b']);assert.equal(next.links.k,'known');
});
