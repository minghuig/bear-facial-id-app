import {test} from 'node:test';
import assert from 'node:assert/strict';
import {browsePhotos, statusGroup} from './photoBrowserModel.ts';

const photos = Array.from({length:500}, (_,i)=>({id:String(i), filename:`Bear ${i}.jpg`, created_at:new Date(2026,0,1+i).toISOString(), detection_state:'complete', status_label:i%2?'Reviewed · 1 confirmed':'Ready to Review', bear_ids:i%3?[]:['bear-a']}));
test('combines filename, status and confirmed identity filters',()=>{
 const result=browsePhotos(photos,{query:' BEAR 1 ',status:'reviewed',bear:'bear-a',sort:'oldest',page:0});
 assert.deepEqual(result.items.map(p=>p.id),['15','105','111','117','123','129','135','141','147','153','159','165','171','177','183','189','195']);
});
test('bounds rendering and clamps a page after results shrink',()=>{
 const result=browsePhotos(photos,{query:'',status:'all',bear:'',sort:'newest',page:99});
 assert.equal(result.total,500);assert.equal(result.page,19);assert.equal(result.items.length,25);assert.equal(result.items.at(-1).id,'0');
 const empty=browsePhotos(photos,{query:'missing',status:'all',bear:'',sort:'newest',page:19});
 assert.equal(empty.page,0);assert.deepEqual(empty.items,[]);
});
test('status categories distinguish partial review, processing and failures',()=>{
 assert.equal(statusGroup({status_label:'Partially reviewed (1/2) · 1 confirmed'}),'needs-review');
 assert.equal(statusGroup({status_label:'Recognition failed — retry'}),'failed');
 assert.equal(statusGroup({status_label:'Recognizing Bears…'}),'processing');
});
