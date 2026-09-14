import { useState } from 'react';
import { ThemeProvider, createTheme } from '@mui/material';
import { PhotoBrowser } from './library/PhotoBrowser';
import { current, initialCandidates } from './fixtures';
import { sortCandidates, type Candidate, type Photo } from './model';
import { confirmSighting, type Collection } from './journeyModel';
import Comparison from './Comparison';
import './journey.css';

const theme=createTheme({palette:{primary:{main:'#315a46'}},typography:{fontFamily:'system-ui, sans-serif',fontSize:13,button:{textTransform:'none'}},components:{MuiButton:{defaultProps:{size:'small'}}}});
const initialRecords=initialCandidates.filter(c=>c.kind==='bear');
const allPhotos:Photo[]=[current,...initialCandidates.flatMap(c=>c.kind==='sighting'?[{...c.photos[0],id:c.id,label:c.label}]:c.photos)];
const initial:Collection={records:initialRecords,links:Object.fromEntries(initialRecords.flatMap(c=>c.photos.map(p=>[p.id,c.id])))};
const filename=(p:Photo)=>p.id==='a'?'IMG_2022.JPG':p.id.length===1?initialCandidates.find(c=>c.id===p.id)!.photos[0].label:p.label;

export default function Journey(){
 const [collection,setCollection]=useState(initial),[selected,setSelected]=useState('a'),[comparing,setComparing]=useState(false);
 const [before,setBefore]=useState<Collection|null>(null),[lastPhoto,setLastPhoto]=useState(''),[notice,setNotice]=useState('');
 const [reviewed,setReviewed]=useState<string[]>([]);
 const photo=allPhotos.find(p=>p.id===selected)!;
 const assigned=collection.records.find(r=>r.id===collection.links[selected])||null;
 const candidates=sortCandidates([...collection.records.map(r=>({...r,photos:r.photos.filter(p=>p.id!==selected)})).filter(r=>r.photos.length>0),...allPhotos.filter(p=>!collection.links[p.id]&&p.id!==selected).map(p=>({id:p.id,label:p.label,kind:'sighting' as const,photos:[p],similarity:initialCandidates.find(c=>c.id===p.id)?.similarity??.901}))].map(c=>({...c,similarity:c.similarity??initialCandidates.find(i=>i.id===c.id)?.similarity})));
 // Keep the inspected candidate list stable during confirmation; return to the library to refresh it.
 const [comparisonMatches,setComparisonMatches]=useState<Candidate[]>([]); const [initialMatchId,setInitialMatchId]=useState<string|undefined>();
 function openComparison(id?:string){setComparisonMatches(candidates);setInitialMatchId(id);setComparing(true);setNotice('');}
 function confirm(match:Candidate){setBefore(collection);setLastPhoto(selected);setCollection(confirmSighting(collection,photo,match));setNotice('Identity confirmed in this demo. The photo library has been updated.');}
 function undo(){if(before){setCollection(before);setBefore(null);setComparing(false);setNotice('Confirmation undone. The sightings are unassigned again.');}}
 const canUndo=before!==null&&lastPhoto===selected;
 const libraryPhotos=allPhotos.map((p,i)=>({id:p.id,filename:filename(p),thumbnail_url:p.src,created_at:new Date(Date.UTC(2026,8,14,12,0,-i)).toISOString(),detection_state:'complete',status_label:collection.links[p.id]?`Reviewed · ${collection.records.find(r=>r.id===collection.links[p.id])!.label}`:reviewed.includes(p.id)?'Reviewed · unidentified':'Ready to Review',bear_ids:collection.links[p.id]?[collection.links[p.id]]:[]}));
 return <ThemeProvider theme={theme}>
  <div className="photo-journey" hidden={comparing}>
   <header><strong>Only Bears</strong><span>Full flow prototype · local demo collection</span><button onClick={()=>{setCollection(initial);setBefore(null);setReviewed([]);setNotice('');setSelected('a');}}>Reset demo</button></header>
   <main className="photos-main"><div className="photos-toolbar"><h1>Photos & review</h1><span>26 demo photos · recognition complete</span></div>
    <div className="photos-layout"><PhotoBrowser photos={libraryPhotos} bears={collection.records.map(r=>({id:r.id,name:r.label}))} selected={selected} onSelect={id=>{setSelected(id);setNotice('');}} pending={[]} loading={false}/>
     <section className="journey-detail" aria-label="Photo review"><div className="journey-photo-heading"><h2>{filename(photo)}</h2><span>{assigned?`Confirmed · ${assigned.label}`:'1 sighting · ready to review'}</span></div>
      {notice&&<div className="confirmation-notice" role="status">{notice}</div>}
      <div className="journey-review-grid"><div className="journey-original"><img src={photo.src} alt={`Selected photo ${filename(photo)}`}/></div><aside className="journey-review-card"><h2>Sighting 1</h2><div className="sighting-status"><img src={photo.src} alt="Sighting preview"/><div><strong>{assigned?assigned.label:reviewed.includes(selected)?'Unidentified':'Unidentified bear'}</strong><small>Recognition complete</small></div></div>
       {assigned?<><p>This sighting is assigned to {assigned.label}.</p><button onClick={()=>openComparison(assigned.id)}>View comparison</button>{canUndo&&<button className="undo-review" onClick={undo}>Undo confirmation</button>}</>:<><h3>Possible matches</h3><p>Compare your sighting with similar photos before confirming an identity.</p><div className="journey-match-previews">{candidates.slice(0,3).map(c=><button key={c.id} onClick={()=>openComparison(c.id)} aria-label={`Open comparison with ${c.label}`}><img src={c.photos[0].src} alt=""/><span><strong>{c.label}</strong><small>Similarity {c.similarity?.toFixed(3)??'—'}</small></span><span>›</span></button>)}</div><button className="confirm-button compare-entry" onClick={()=>openComparison()}>Compare matches →</button><button className="keep-unidentified" onClick={()=>{setReviewed([...new Set([...reviewed,selected])]);setNotice('Reviewed and kept unidentified. You can compare again at any time.');}}>Keep unidentified</button></>}
       <small className="journey-demo-note">Demo matches and scores. Changes stay in this tab.</small>
      </aside></div>
     </section>
    </div>
   </main>
  </div>
  {comparing&&<Comparison key={selected} current={{...photo,label:filename(photo)}} matches={comparisonMatches} initialMatchId={initialMatchId} confirmed={assigned} onConfirm={confirm} onUndo={canUndo?undo:undefined} onBack={()=>setComparing(false)}/>}
 </ThemeProvider>;
}
