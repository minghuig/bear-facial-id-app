import { useRef, useState, type ReactNode } from 'react';
import { Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import { buildAssignment, type Candidate, type Photo } from './model';
import { current, initialCandidates } from './fixtures';

function PhotoImage({photo}: {photo:Photo}) {
 const [failed,setFailed]=useState(false);
 return failed?<span className="missing">Private demo photo missing. Run the photo preparation script in docs/COMPARISON_PROTOTYPE.md.</span>:<img src={photo.src} alt={photo.label} onError={()=>setFailed(true)}/>;
}
function Modal({title,children,onClose,actions,wide=false}: {title:string;children:ReactNode;onClose:()=>void;actions?:ReactNode;wide?:boolean}) {
 return <Dialog open onClose={onClose} fullWidth maxWidth={wide?'xl':'md'} PaperProps={{className:'prototype-dialog'}}><DialogTitle><span>{title}</span><button className="icon-button" onClick={onClose} aria-label="Close dialog">×</button></DialogTitle><DialogContent>{children}</DialogContent>{actions&&<DialogActions>{actions}</DialogActions>}</Dialog>;
}
export default function Comparison(){
 const [candidates,setCandidates]=useState<Candidate[]>(initialCandidates);
 const [compared,setCompared]=useState<string[]>(['cedar','b']);
 const [selected,setSelected]=useState<string[]>([]),[destination,setDestination]=useState('');
 const [indices,setIndices]=useState<Record<string,number>>({});
 const [viewed,setViewed]=useState<Record<string,number[]>>({cedar:[0],b:[0]});
 const [search,setSearch]=useState(''),[filter,setFilter]=useState('all');
 const [gallery,setGallery]=useState<string|null>(null),[zoom,setZoom]=useState<Photo[]|null>(null),[zoomScale,setZoomScale]=useState(1);
 const [reviewing,setReviewing]=useState(false),[notice,setNotice]=useState(''),[saved,setSaved]=useState(false),[kept,setKept]=useState(false);
 const undo=useRef<Candidate[]|null>(null);
 const candidate=(id:string)=>candidates.find(c=>c.id===id)!;
 const chosen=destination&&destination!=='new'?candidate(destination):null;
 const additions=[current,...selected.map(id=>({...candidate(id).photos[0],label:candidate(id).label}))];
 const visible=candidates.filter(c=>(filter==='all'||c.kind===filter)&&c.label.toLowerCase().includes(search.toLowerCase()));
 function selectReference(id:string,i:number){setIndices(v=>({...v,[id]:i}));setViewed(v=>({...v,[id]:[...new Set([...(v[id]||[0]),i])]}));}
 function toggleCompare(id:string){
  if(compared.includes(id)){setCompared(compared.filter(x=>x!==id));return;}
  if(compared.length===3){setNotice('Three candidates are open. Remove one to compare another.');return;}
  setCompared([...compared,id]);setViewed(v=>({...v,[id]:v[id]||[0]}));
 }
 function toggleSelected(id:string){setKept(false);setSelected(v=>v.includes(id)?v.filter(x=>x!==id):[...v,id]);}
 function openZoom(photos:Photo[]){setZoomScale(1);setZoom(photos);}
 function reset(){setSearch('');setFilter('all');setCandidates(initialCandidates);setCompared(['cedar','b']);setSelected([]);setDestination('');setIndices({});setViewed({cedar:[0],b:[0]});setSaved(false);setKept(false);setNotice('Demo reset. All sightings are back in their original state.');undo.current=null;}
 function save(){
  const assignment=buildAssignment(current.id,selected,destination,candidates);
  undo.current=candidates;
  const recordId=assignment.destination==='new'?'unnamed-08':assignment.destination;
  const next=candidates.filter(c=>!selected.includes(c.id));
  if(assignment.destination==='new')next.unshift({id:recordId,label:'Unnamed bear 08',kind:'bear',photos:additions});
  else {const i=next.findIndex(c=>c.id===recordId);next[i]={...next[i],photos:[...next[i].photos,...additions]};}
  setCandidates(next);setCompared([recordId]);setSelected([]);setDestination(recordId);setSaved(true);setReviewing(false);
  setNotice(`Demo saved: ${additions.length} sighting${additions.length===1?'':'s'} ${assignment.destination==='new'?'grouped as Unnamed bear 08':`added to ${chosen!.label}`}. Your real collection is unchanged.`);
 }
 function undoSave(){if(!undo.current)return;setCandidates(undo.current);setSaved(false);setDestination('');setSelected([]);setIndices({});setViewed({cedar:[0],b:[0]});setCompared(['cedar','b']);setNotice('Assignment undone. The sightings are unassigned again.');undo.current=null;}
 const displayed=compared.map(candidate).filter(Boolean);
 return <div className="compare-app">
  <header className="topbar"><a className="brand" href="/comparison.html"><span className="brand-mark">◒</span> Only Bears</a><span className="prototype-tag">INTERACTIVE PROTOTYPE</span><span className="demo-description">Demo records · real field photos · changes stay in this tab</span><button onClick={reset}>Reset demo</button></header>
  <main>
   <div className="page-heading"><div><div className="eyebrow">IDENTIFICATION WORKSPACE</div><h1>Compare before you decide.</h1><p>Explore complete bear galleries and unassigned sightings together.</p></div><div className="reviewing-badge"><span className="status-dot"/> {saved?'Assignment reviewed':kept?'Reviewed · unassigned':'Reviewing sighting A'}</div></div>
   {notice&&<div className="notice" role="status"><span>{notice}</span><button className="icon-button" onClick={()=>setNotice('')} aria-label="Dismiss notice">×</button></div>}
   <section className="candidate-section" aria-label="Candidate selection"><div className="section-top"><h2>Explore possible matches <span>{candidates.length}</span></h2><div className="candidate-tools"><div className="segmented" aria-label="Filter candidates">{[['all','All'],['bear','Bear records'],['sighting','Unassigned']].map(([v,l])=><button key={v} className={filter===v?'active':''} onClick={()=>setFilter(v)} aria-pressed={filter===v}>{l}</button>)}</div><input aria-label="Search candidates" placeholder="Find a bear or sighting…" value={search} onChange={e=>setSearch(e.target.value)}/></div></div>
    <div className="candidate-tray">{visible.map(c=><button key={c.id} className={`candidate-tile ${compared.includes(c.id)?'is-open':''}`} onClick={()=>toggleCompare(c.id)} aria-pressed={compared.includes(c.id)} aria-label={`${compared.includes(c.id)?'Remove':'Compare'} ${c.label}`}><PhotoImage photo={c.photos[0]}/><span><strong>{c.label}</strong><small>{c.kind==='bear'?`Bear record · ${c.photos.length} photos`:'Unassigned · 1 photo'}</small></span><span className="tile-action">{compared.includes(c.id)?'✓':'+'}</span></button>)}{!visible.length&&<p className="muted">No matches for this search.</p>}</div>
   </section>
   <section className="comparison-section" aria-label="Side by side comparison"><div className="section-top"><h2>Side by side <span>{displayed.length} / 3 candidates</span></h2><div className="compare-hint">Browsing a photo does not assign it.</div></div>
    <div className="comparison-grid" style={{gridTemplateColumns:`repeat(${1+Math.max(1,displayed.length)}, minmax(260px, 1fr))`}}>
     <article className="photo-panel current-panel"><div className="panel-title"><div><span className="eyebrow">CURRENT SIGHTING</span><h3>Sighting A</h3></div><span className="pin-label">Pinned</span></div><button className="large-photo" onClick={()=>openZoom([current])} aria-label="Enlarge current sighting"><PhotoImage photo={current}/><span className="enlarge-label">⤢ Enlarge</span></button><div className="panel-details"><strong>Your photo under review</strong><p>{saved?'Included in your demo assignment.':'Keep this photo in view as you inspect each candidate.'}</p><span className="state-label">{saved?'Assigned in demo':'Unassigned sighting'}</span></div></article>
     {displayed.map(c=>{const i=Math.min(indices[c.id]||0,c.photos.length-1);return <article className="photo-panel" key={c.id}><div className="panel-title"><div><span className="eyebrow">{c.kind==='bear'?'BEAR RECORD':'UNASSIGNED SIGHTING'}</span><h3>{c.label}</h3></div><button className="icon-button" onClick={()=>toggleCompare(c.id)} aria-label={`Close ${c.label}`}>×</button></div><button className="large-photo" onClick={()=>openZoom([current,c.photos[i]])} aria-label={`Enlarge comparison with ${c.label}`}><PhotoImage photo={c.photos[i]}/><span className="enlarge-label">⤢ Compare enlarged</span></button>
      <div className="gallery-controls"><button disabled={i===0} onClick={()=>selectReference(c.id,i-1)} aria-label={`Previous photo of ${c.label}`}>←</button><span>Photo {i+1} of {c.photos.length}</span><button disabled={i===c.photos.length-1} onClick={()=>selectReference(c.id,i+1)} aria-label={`Next photo of ${c.label}`}>→</button></div>
      <div className="reference-strip">{c.photos.map((p,j)=><button key={p.id} aria-label={`${c.label} photo ${j+1}`} aria-pressed={i===j} className={i===j?'selected':''} onClick={()=>selectReference(c.id,j)}><PhotoImage photo={p}/>{(viewed[c.id]||[0]).includes(j)&&<span className="seen-dot"/>}</button>)}</div>
      <div className="panel-bottom">{c.kind==='bear'?<><div className="gallery-summary"><button className="text-button" onClick={()=>setGallery(c.id)}>View all {c.photos.length} photos</button><small>{(viewed[c.id]||[0]).length} viewed</small></div><button className={`choose-button ${destination===c.id?'chosen':''}`} disabled={saved} onClick={()=>{setDestination(c.id);setKept(false);}}>{destination===c.id?'✓ Selected bear record':'Use this bear record…'}</button></>:<><p className="small-note">A separate sighting. No identity has been established.</p><label className={`include-control ${selected.includes(c.id)?'included':''}`}><input type="checkbox" checked={selected.includes(c.id)} disabled={saved} onChange={()=>toggleSelected(c.id)}/> Include in proposed assignment</label></>}</div>
     </article>;})}
     {!displayed.length&&<div className="empty-comparison"><span>＋</span><h3>Bring a candidate into view</h3><p>Choose a bear record or an unassigned sighting above.</p></div>}
    </div>
    {displayed.length>1&&<div className="comparison-extras"><button onClick={()=>openZoom(displayed.map(c=>c.photos[Math.min(indices[c.id]||0,c.photos.length-1)]))}>Compare candidate photos enlarged</button><span>Inspect differences between the candidates themselves.</span></div>}
   </section>
   <section className="sighting-selection" aria-label="Sightings to assign"><div><h2>Which sightings belong in this assignment?</h2><p>Only checked sightings will be added. Leave uncertain photos out.</p></div><div className="selection-strip"><div className="selection-item mandatory"><PhotoImage photo={current}/><span>Sighting A <small>Current · included</small></span><span>✓</span></div>{candidates.filter(c=>c.kind==='sighting').map(c=><label className={`selection-item ${selected.includes(c.id)?'included':''}`} key={c.id}><PhotoImage photo={c.photos[0]}/><span>{c.label}<small>Unassigned</small></span><input aria-label={`Include ${c.label}`} type="checkbox" disabled={saved} checked={selected.includes(c.id)} onChange={()=>toggleSelected(c.id)}/></label>)}</div></section>
  </main>
  <footer className="draft-bar"><div className="draft-title"><span className="eyebrow">PROPOSED ASSIGNMENT</span><strong>{saved?'Saved in this demo':`${additions.length} sighting${additions.length===1?'':'s'} selected`}</strong></div><label className="destination-field">Bear record<select aria-label="Assignment destination" disabled={saved} value={destination} onChange={e=>{setDestination(e.target.value);setKept(false);}}><option value="">Choose a destination…</option><option value="new">＋ New unnamed bear</option>{candidates.filter(c=>c.kind==='bear').map(c=><option key={c.id} value={c.id}>{c.label} · {c.photos.length} photos</option>)}</select></label><div className="draft-actions">{saved&&<button onClick={undoSave}>Undo assignment</button>}<button disabled={saved} onClick={()=>{setSelected([]);setDestination('');setKept(true);setNotice('Review saved in this demo. Sighting A stays unassigned and available for comparison.');}}>Keep unassigned</button><button className="primary" disabled={!destination||saved} onClick={()=>setReviewing(true)}>Review assignment <span>→</span></button></div></footer>
  {gallery&&<Modal wide title={`${candidate(gallery).label} · complete gallery`} onClose={()=>setGallery(null)}><p className="muted">All {candidate(gallery).photos.length} assigned photos. Choose one to inspect beside your current sighting.</p><div className="contact-sheet">{candidate(gallery).photos.map((p,i)=><button key={p.id} onClick={()=>{selectReference(gallery,i);setGallery(null);}}><PhotoImage photo={p}/><span>Photo {i+1} · {p.label}</span></button>)}</div></Modal>}
  {zoom&&<Modal wide title="Inspect the evidence" onClose={()=>setZoom(null)}><div className="zoom-toolbar"><span>Scroll each image independently when enlarged.</span><label>Zoom <select aria-label="Image zoom" value={zoomScale} onChange={e=>setZoomScale(Number(e.target.value))}><option value={1}>Fit</option><option value={1.5}>150%</option><option value={2}>200%</option><option value={3}>300%</option></select></label></div><div className="zoom-grid" style={{gridTemplateColumns:`repeat(${zoom.length}, minmax(240px,1fr))`}}>{zoom.map((p,i)=><div key={`${p.id}-${i}`}><p className="zoom-caption">{p.label}</p><div className="zoom-viewport"><div style={{width:`${zoomScale*100}%`}}><PhotoImage photo={p}/></div></div></div>)}</div></Modal>}
  {reviewing&&<Modal wide title="Review the complete assignment" onClose={()=>setReviewing(false)} actions={<><button onClick={()=>setReviewing(false)}>Back to comparison</button><button className="primary" onClick={save}>{destination==='new'?`Create unnamed bear with ${additions.length} sighting${additions.length===1?'':'s'}`:`Add ${additions.length} sighting${additions.length===1?'':'s'} to ${chosen!.label}`}</button></>}><div className="review-intro"><h2>{destination==='new'?'Create a new unnamed bear':`Add sightings to ${chosen!.label}`}</h2><p>This records that every photo below depicts one individual. Leave out any sighting you cannot confidently assign.</p><span className="prototype-tag">SIMULATED SAVE · YOUR COLLECTION IS UNCHANGED</span></div>{chosen&&<><h3>Already assigned · {chosen.photos.length} photos</h3><div className="review-gallery">{chosen.photos.map(p=><button key={p.id} onClick={()=>openZoom([current,p])} aria-label={`Inspect existing ${p.label}`}><PhotoImage photo={p}/></button>)}</div></>}<h3>{destination==='new'?'Sightings in the new record':'Sightings being added'} · {additions.length}</h3><div className="review-additions">{additions.map((p,i)=><div key={p.id}><button onClick={()=>openZoom([p])} aria-label={`Inspect addition ${p.label}`}><PhotoImage photo={p}/></button><div><strong>{p.label}</strong>{i===0?<small>Current sighting</small>:<button className="text-button" onClick={()=>setSelected(v=>v.filter(id=>id!==selected[i-1]))}>Remove</button>}</div></div>)}</div><p className="small-note">Other bear records remain separate. Unselected sightings remain unassigned.</p></Modal>}
 </div>;
}
