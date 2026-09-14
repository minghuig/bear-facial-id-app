import { useState } from 'react';
import { Dialog, DialogContent, DialogTitle } from '@mui/material';
import { current, initialCandidates } from './fixtures';
import { sortCandidates, type Photo } from './model';

const matches = sortCandidates(initialCandidates);
function Picture({photo}: {photo:Photo}) {
 return <img src={photo.src} alt={photo.label}/>;
}

export default function Comparison() {
 const [matchIndex,setMatchIndex] = useState(0);
 const [photoIndex,setPhotoIndex] = useState(0);
 const [enlarged,setEnlarged] = useState(false);
 const match = matches[matchIndex];
 const reference = match.photos[photoIndex];
 function chooseMatch(index:number) { setMatchIndex(index); setPhotoIndex(0); }
 const pair = <div className="photo-pair">
  <figure><figcaption><strong>Your sighting</strong><span>Unidentified</span></figcaption><div className="image-surface"><Picture photo={current}/></div></figure>
  <figure><figcaption><strong>{match.label}</strong><span>{match.kind==='bear'?`${match.photos.length} photos`:'Unidentified'} · similarity {match.similarity?.toFixed(3)}</span></figcaption><div className="image-surface"><Picture photo={reference}/></div></figure>
 </div>;
 return <div className="simple-viewer">
  <header><strong>Only Bears</strong><span>Comparison prototype · demo matches & scores</span></header>
  <main>
   <div className="viewer-heading"><h1>Compare photos</h1><button onClick={()=>setEnlarged(true)}>Enlarge photos ↗</button></div>
   {pair}
   <div className="below-photos"><p>Your sighting stays here while you browse matches.</p><div className="reference-gallery">
    {match.photos.length>1?<><div className="gallery-heading"><span>All photos of {match.label}</span><div><button aria-label="Previous reference photo" disabled={photoIndex===0} onClick={()=>setPhotoIndex(photoIndex-1)}>←</button><span>{photoIndex+1} / {match.photos.length}</span><button aria-label="Next reference photo" disabled={photoIndex===match.photos.length-1} onClick={()=>setPhotoIndex(photoIndex+1)}>→</button></div></div><div className="reference-strip">{match.photos.map((photo,index)=><button key={photo.id} aria-label={`${match.label} photo ${index+1}`} aria-pressed={photoIndex===index} onClick={()=>setPhotoIndex(index)}><Picture photo={photo}/></button>)}</div></>:<p>This sighting has one photo.</p>}
   </div></div>
   <section aria-label="Similar sightings"><div className="matches-heading"><h2>Similar sightings</h2><span>Highest similarity first</span></div><div className="match-strip">{matches.map((candidate,index)=><button key={candidate.id} aria-label={`Compare ${candidate.label}`} aria-pressed={matchIndex===index} onClick={()=>chooseMatch(index)}><Picture photo={candidate.photos[0]}/><span><strong>{candidate.label}</strong><small>{candidate.photos.length} photo{candidate.photos.length===1?'':'s'} · {candidate.similarity?.toFixed(3)}</small></span></button>)}</div></section>
  </main>
  <Dialog open={enlarged} onClose={()=>setEnlarged(false)} fullWidth maxWidth="xl" PaperProps={{className:'enlarged-view'}}><DialogTitle><span>Compare photos</span><button onClick={()=>setEnlarged(false)}>Close</button></DialogTitle><DialogContent>{pair}</DialogContent></Dialog>
 </div>;
}
