import React,{useEffect,useMemo,useRef,useState} from 'react';
import {Autocomplete,Button,Chip,CircularProgress,MenuItem,TextField} from '@mui/material';
import {browsePhotos,statusGroup,statusOptions} from './photoBrowserModel';
import type {BrowserPhoto} from './photoBrowserModel';

type Photo=BrowserPhoto&{thumbnail_url:string};
type Bear={id:string;name:string|null};
const bearLabel=(b:Bear)=>b.name||`Unknown bear · ${b.id.slice(0,8)}`;
export function PhotoBrowser({photos,bears,selected,onSelect,pending,loading}:{photos:Photo[];bears:Bear[];selected:string;onSelect:(id:string)=>void;pending:{name:string;url:string}[];loading:boolean}){
 const [query,setQuery]=useState(''),[status,setStatus]=useState('all'),[bear,setBear]=useState(''),[sort,setSort]=useState('newest'),[page,setPage]=useState(0);
 const list=useRef<HTMLDivElement>(null);
 const results=useMemo(()=>browsePhotos(photos,{query,status,bear,sort,page}),[photos,query,status,bear,sort,page]);
 useEffect(()=>{setPage(results.page);},[results.page]);
 useEffect(()=>{list.current?.scrollTo(0,0);},[query,status,bear,sort,results.page]);
 const clear=()=>{setQuery('');setStatus('all');setBear('');setPage(0);};
 const filtered=!!query||status!=='all'||!!bear;
 return <aside className="collection-list photo-browser" aria-label="Photo library">
  <div className="library-heading"><strong>Photo library</strong><Chip size="small" label={photos.length}/></div>
  <div className="library-controls">
   <TextField size="small" fullWidth label="Search filenames" value={query} onChange={e=>{setQuery(e.target.value);setPage(0);}}/>
   <div className="library-filter-row">
    <TextField select size="small" label="Status" value={status} onChange={e=>{setStatus(e.target.value);setPage(0);}}>{statusOptions.map(([value,label])=><MenuItem key={value} value={value}>{label}</MenuItem>)}</TextField>
    <TextField select size="small" label="Sort by" value={sort} onChange={e=>{setSort(e.target.value);setPage(0);}}><MenuItem value="newest">Newest upload</MenuItem><MenuItem value="oldest">Oldest upload</MenuItem><MenuItem value="name">Filename A–Z</MenuItem></TextField>
   </div>
   <Autocomplete size="small" options={bears} value={bears.find(b=>b.id===bear)||null} getOptionLabel={bearLabel} isOptionEqualToValue={(a,b)=>a.id===b.id} onChange={(_,value)=>{setBear(value?.id||'');setPage(0);}} renderInput={params=><TextField {...params} label="Contains bear" placeholder="Any confirmed bear"/>}/>
   <div className="library-results" aria-live="polite"><span>{results.total} of {photos.length} photos</span>{filtered&&<Button onClick={clear}>Clear filters</Button>}</div>
  </div>
  {selected&&!results.ids.has(selected)&&<div className="library-selection-note">The open photo is outside these filters.</div>}
  <div className="collection-items" ref={list}>
   {pending.map(p=><div key={p.url} className="collection-item" aria-busy="true"><img src={p.url} alt=""/><span className="item-copy"><span className="item-name">{p.name}</span><span className="item-state">Uploading…</span></span><CircularProgress size={16}/></div>)}
   {results.items.map(p=><button type="button" key={p.id} className="collection-item" aria-current={selected===p.id?'true':undefined} onClick={()=>onSelect(p.id)}>
    <img src={p.thumbnail_url} alt="" loading="lazy" decoding="async"/>
    <span className="item-copy"><span className="item-name" title={p.filename}>{p.filename}</span><span className={`item-state status-${statusGroup(p)}`}>{p.status_label||'Processing…'}</span><span className="item-date">{p.created_at?new Date(p.created_at).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'}):'Upload date unavailable'}</span></span>
   </button>)}
   {!results.total&&<div className="library-empty"><strong>{loading?'Loading photos…':photos.length?'No matching photos':'Your collection starts here'}</strong><p>{photos.length?'Try another filename or clear your filters.':'Upload bear photos to begin reviewing.'}</p>{filtered&&<Button onClick={clear}>Clear filters</Button>}</div>}
  </div>
  <div className="library-pagination"><Button aria-label="Previous photo page" disabled={results.page===0} onClick={()=>setPage(results.page-1)}>Previous</Button><span>{results.total?`${results.page*25+1}–${Math.min((results.page+1)*25,results.total)}`:'0'} / {results.total}</span><Button aria-label="Next photo page" disabled={results.page+1>=results.pages} onClick={()=>setPage(results.page+1)}>Next</Button></div>
 </aside>;
}
