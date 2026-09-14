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

test('reidentification moves only current photo between existing identities',()=>{
 const old={records:[{...state.records[0],photos:[a,state.records[0].photos[0]]},{id:'other',label:'Other',kind:'bear' as const,photos:[b]}],links:{a:'known',k:'known',b:'other'}};
 const next=confirmSighting(old,a,old.records[1]);
 assert.deepEqual(next.records[0].photos.map(p=>p.id),['k']);
 assert.deepEqual(next.records[1].photos.map(p=>p.id),['b','a']);
 assert.deepEqual(next.links,{a:'other',k:'known',b:'other'});
 assert.equal(old.records[0].photos.length,2);
});
test('reidentification to an unassigned sighting leaves former group mates unchanged',()=>{
 const old={records:[{...state.records[0],photos:[a,state.records[0].photos[0]]}],links:{a:'known',k:'known'}};
 const next=confirmSighting(old,a,{id:'b',label:'B',kind:'sighting',photos:[b]});
 assert.equal(next.links.a,next.links.b);assert.equal(next.links.k,'known');assert.deepEqual(next.records[0].photos.map(p=>p.id),['k']);
});
test('confirming current identity does not duplicate its photo',()=>{
 const old=confirmSighting(state,a,state.records[0]);
 assert.deepEqual(confirmSighting(old,a,old.records[0]),old);
});
