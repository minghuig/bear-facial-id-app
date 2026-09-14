import { useState } from 'react';
import { Dialog, DialogActions, DialogContent, DialogTitle } from '@mui/material';
import { type Candidate, type Photo } from './model';

function Picture({photo}: {photo:Photo}) {
 return <img src={photo.src} alt={photo.label}/>;
}

export default function Comparison({current,matches,initialMatchId,confirmed,onConfirm,onUndo,onBack}: {current:Photo;matches:Candidate[];initialMatchId?:string;confirmed:Candidate|null;onConfirm:(match:Candidate)=>void;onUndo?:()=>void;onBack:()=>void}) {
 const [matchIndex,setMatchIndex] = useState(Math.max(0,matches.findIndex(m=>m.id===initialMatchId)));
 const [photoIndex,setPhotoIndex] = useState(0);
 const [confirming,setConfirming] = useState(false); const [completed,setCompleted] = useState(false);
 const match = matches[matchIndex];
 const reference = match.photos[photoIndex];
 function chooseMatch(index:number) { setMatchIndex(index); setPhotoIndex(0); }
 function confirmMatch() {
  onConfirm(match); setConfirming(false); setCompleted(true);
 }
 const pair = <div className="photo-pair">
  <figure><figcaption><strong>Your sighting</strong><span>{confirmed?'Confirmed in demo':'Unidentified'}</span></figcaption><div className="image-surface"><Picture photo={current}/></div></figure>
  <figure><figcaption><strong>{match.label}</strong><span>{match.kind==='bear'?`${match.photos.length} photo${match.photos.length===1?'': 's'}`:'Unidentified'} · similarity {match.similarity?.toFixed(3)??'—'}</span></figcaption><div className="image-surface"><Picture photo={reference}/></div></figure>
 </div>;
 return <div className="simple-viewer">
  <header><strong>Only Bears</strong><span>Comparison prototype · demo matches & scores</span></header>
  <main>
   <div className="viewer-heading"><div><button className="back-link" onClick={onBack}>← Back to photos</button><h1>Compare photos</h1></div><span className="comparison-filename">{current.label}</span></div>
   {confirmed&&<div className="confirmation-notice" role="status"><span>Your sighting is assigned to {confirmed.label}. <small>Demo only.</small></span><div>{onUndo&&<button onClick={onUndo}>Undo</button>} <button onClick={onBack}>Return to photo</button></div></div>}
   {pair}
   <div className="below-photos"><p>Your sighting stays here while you browse matches.</p><div className="reference-gallery">
    {match.photos.length>1?<><div className="gallery-heading"><span>All photos of {match.label}</span><div><button aria-label="Previous reference photo" disabled={photoIndex===0} onClick={()=>setPhotoIndex(photoIndex-1)}>←</button><span>{photoIndex+1} / {match.photos.length}</span><button aria-label="Next reference photo" disabled={photoIndex===match.photos.length-1} onClick={()=>setPhotoIndex(photoIndex+1)}>→</button></div></div><div className="reference-strip">{match.photos.map((photo,index)=><button key={photo.id} aria-label={`${match.label} photo ${index+1}`} aria-pressed={photoIndex===index} onClick={()=>setPhotoIndex(index)}><Picture photo={photo}/></button>)}</div></>:<p>This sighting has one photo.</p>}
    <div className="confirm-action"><span>{confirmed?'Only this sighting will move. Other photos stay assigned.':'Confident these are the same bear?'}</span><button className="confirm-button" disabled={completed||match.id===confirmed?.id} onClick={()=>setConfirming(true)}>{match.id===confirmed?.id?'Current identity':confirmed?'Change identity':'Confirm same bear'}</button></div>
   </div></div>
   <section aria-label="Similar sightings"><div className="matches-heading"><h2>Similar sightings</h2><span>Highest similarity first</span></div><div className="match-strip">{matches.map((candidate,index)=><button key={candidate.id} aria-label={`Compare ${candidate.label}`} aria-pressed={matchIndex===index} onClick={()=>chooseMatch(index)}><Picture photo={candidate.photos[0]}/><span><strong>{candidate.label}</strong><small>{candidate.photos.length} photo{candidate.photos.length===1?'':'s'} · {candidate.similarity?.toFixed(3)??'—'}</small></span></button>)}</div></section>
  </main>
  <Dialog open={confirming} onClose={()=>setConfirming(false)} fullWidth maxWidth="xs" PaperProps={{className:'confirm-dialog'}}><DialogTitle>{confirmed?'Change this sighting’s identity?':'Confirm same bear?'}</DialogTitle><DialogContent><div className="confirm-thumbnails"><Picture photo={current}/><Picture photo={reference}/></div><p>{confirmed&&`Remove this sighting from ${confirmed.label}. `}{match.kind==='bear'?`Add your sighting to ${match.label}, which already has ${match.photos.length} photos.`:`Link your sighting and ${match.label} as one unknown bear.`}</p><small>Other sightings stay unchanged. This prototype only simulates saving.</small></DialogContent><DialogActions><button onClick={()=>setConfirming(false)}>Back to photos</button><button className="confirm-button" onClick={confirmMatch}>{confirmed?'Confirm change':'Yes, same bear'}</button></DialogActions></Dialog>
 </div>;
}
