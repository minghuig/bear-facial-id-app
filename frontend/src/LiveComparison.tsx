import {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Alert, Button, Dialog, DialogTitle, DialogContent, DialogActions} from '@mui/material';
import './live-comparison.css';

type Picture={id:string;src:string;label:string};
type Match={id:string;label:string;kind:'bear'|'sighting';similarity:number;reference_id:string;bear_id:string|null;photos:Picture[]};
type Head={id:string;crop_url:string;bear_id:string|null;review_state:string};
type Matches={head:Head;candidates:Match[]};
type Undo={head_review_id:string;reference_review_id:string|null};
export default function LiveComparison({headId,filename,bears,orgId,api,onBack,onChanged}:{headId:string;filename:string;orgId:string;api:<T>(path:string,method?:string,body?:unknown)=>Promise<T>;bears:{id:string;name:string|null}[];onBack:()=>void;onChanged:()=>void}){
 const request=<T,>(path:string,body?:unknown)=>api<T>(path,body===undefined?'GET':'POST',body);
 const [selected,setSelected]=useState(''),[photoId,setPhotoId]=useState(''),[pending,setPending]=useState<{head:Head;match:Match}|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[undo,setUndo]=useState<Undo|null>(null),[saved,setSaved]=useState('');
 const query=useQuery({queryKey:[orgId,'comparison',headId],queryFn:()=>request<Matches>(`/api/heads/${headId}/matches`),refetchInterval:pending||busy?false:5000});
 const data=query.data;
 const matches=[...(data?.candidates||[])].sort((a,b)=>b.similarity-a.similarity);
 const match=matches.find(m=>m.id===selected)||matches[0];
 const picture=match?.photos.find(p=>p.id===photoId)||match?.photos[0];
 const currentName=data?.head.bear_id?(bears.find(b=>b.id===data.head.bear_id)?.name||`Unnamed bear · ${data.head.bear_id.slice(0,8)}`):'Unidentified';
 async function confirm(){
  if(!pending)return;setBusy(true);setError('');
  try{const result=await request<{head:Head;undo:Undo}>(`/api/heads/${headId}/match`,{reference_id:pending.match.reference_id,expected_bear_id:pending.head.bear_id,expected_review_state:pending.head.review_state,expected_reference_bear_id:pending.match.bear_id});setUndo(result.undo);setSaved('Identity saved.');setPending(null);onChanged();await query.refetch();}
  catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}
 }
 async function undoMatch(){if(!undo)return;setBusy(true);setError('');try{await request(`/api/heads/${headId}/undo-match`,undo);setUndo(null);setSaved('Previous identity restored.');onChanged();await query.refetch();}catch(e){setError(String(e instanceof Error?e.message:e));}finally{setBusy(false);}}
 return <section className="live-comparison" aria-label="Compare bear photos">
  <div className="lc-heading"><div><Button onClick={onBack} disabled={busy}>← Back to photos</Button><h1>Compare photos</h1></div><span>{filename}</span></div>
  {(error||query.error)&&<Alert severity="error" action={<Button onClick={()=>{setPending(null);setError('');void query.refetch();}}>Reload matches</Button>}>{error||String(query.error)}</Alert>}
  {saved&&<Alert severity="success" action={undo?<Button disabled={busy} onClick={()=>void undoMatch()}>Undo</Button>:undefined}>{saved}</Alert>}
  {query.isPending?<p role="status">Loading similar sightings…</p>:data&&<>
   <div className="lc-pair">
    <figure><figcaption><strong>Your sighting</strong><span>{currentName}</span></figcaption><div className="lc-image"><img src={data.head.crop_url} alt={`Your sighting in ${filename}`}/></div></figure>
    <figure><figcaption><strong>{match?.label||'No similar sightings yet'}</strong><span>{match?`${match.photos.length} photos · similarity ${match.similarity.toFixed(3)}`:'Recognized, unidentified sightings can appear here too.'}</span></figcaption><div className="lc-image">{picture?<img src={picture.src} alt={picture.label}/>:<p>No eligible matches. Return to the photo to leave it unidentified or create a new bear.</p>}</div></figure>
   </div>
   {match&&<div className="lc-below"><p>Similarity helps you compare; it is not the probability of a match.</p><div>
    <div className="lc-gallery-heading"><span>{match.kind==='bear'?`Photos of ${match.label}`:'Unidentified sighting'}</span><span>{Math.max(0,match.photos.findIndex(p=>p.id===picture?.id))+1} / {match.photos.length}</span></div>
    <div className="lc-references">{match.photos.map((photo,i)=><button key={photo.id} aria-label={`${match.label} photo ${i+1}`} aria-pressed={picture?.id===photo.id} onClick={()=>setPhotoId(photo.id)}><img src={photo.src} alt="" loading="lazy"/></button>)}</div>
    <div className="lc-action"><span>{data.head.bear_id?'Only this sighting will move.':'Confident these are the same bear?'}</span><Button variant="contained" disabled={busy||!!query.error||match.bear_id!==null&&match.bear_id===data.head.bear_id} onClick={()=>{setError('');setPending({head:{...data.head},match});}}>{match.bear_id!==null&&match.bear_id===data.head.bear_id?'Current identity':data.head.bear_id?'Change identity':'Confirm same bear'}</Button></div>
   </div></div>}
   <div className="lc-matches-heading"><h2>Similar sightings</h2><span>Highest similarity first</span></div>
   <div className="lc-matches">{matches.map(candidate=><button key={candidate.id} aria-label={`Compare ${candidate.label}`} aria-pressed={match?.id===candidate.id} onClick={()=>{setSelected(candidate.id);setPhotoId('');}}><img src={candidate.photos[0]?.src} alt="" loading="lazy"/><span><strong>{candidate.label}</strong><small>{candidate.photos.length} photos · {candidate.similarity.toFixed(3)}</small></span></button>)}</div>
  </>}
  <Dialog open={!!pending} onClose={()=>{if(!busy)setPending(null);}} fullWidth maxWidth="xs"><DialogTitle>{pending?.head.bear_id?'Change this sighting’s identity?':'Confirm same bear?'}</DialogTitle><DialogContent><p>{pending?.head.bear_id&&`Remove only this sighting from ${currentName}. `}{pending?.match.kind==='bear'?`Add it to ${pending.match.label}.`:'Link these two sightings as one unnamed bear.'}</p><p>Other photos keep their current identities.</p>{error&&<Alert severity="error">{error}</Alert>}</DialogContent><DialogActions><Button disabled={busy} onClick={()=>setPending(null)}>Keep comparing</Button><Button variant="contained" disabled={busy} onClick={()=>void confirm()}>{busy?'Saving…':pending?.head.bear_id?'Confirm change':'Yes, same bear'}</Button></DialogActions></Dialog>
 </section>;
}
