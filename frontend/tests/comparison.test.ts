import { strict as assert } from 'node:assert';
import { test } from 'node:test';
import { buildAssignment } from '../src/comparison/model.ts';
const candidates = [
  { id:'known', label:'Bear 12', kind:'bear' as const, photos:[{id:'k1',src:'k1',label:'Known'}] },
  { id:'b', label:'Sighting B', kind:'sighting' as const, photos:[{id:'b',src:'b',label:'B'}] },
];
test('existing assignment includes only explicitly selected unassigned sightings',()=>{
  assert.deepEqual(buildAssignment('a',['b'],'known',candidates),{destination:'known',sightingIds:['a','b']});
});
test('new identity contains the current sighting exactly once',()=>{
  assert.deepEqual(buildAssignment('a',['a','b','b'],'new',candidates),{destination:'new',sightingIds:['a','b']});
});
test('an established identity cannot be silently merged as a sighting',()=>{
  assert.throws(()=>buildAssignment('a',['known'],'new',candidates),/unassigned/);
});
test('destination must be an existing bear or explicitly new',()=>{
  assert.throws(()=>buildAssignment('a',[],'b',candidates),/destination/);
  assert.throws(()=>buildAssignment('a',[],'',candidates),/destination/);
});
