import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {QueryClient, QueryClientProvider, useQuery} from '@tanstack/react-query';
import {Alert, AppBar, Button, Card, CardContent, Chip, CircularProgress, Container, CssBaseline, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Select, Stack, Tab, Tabs, TextField, ThemeProvider, Toolbar, Tooltip, Typography, createTheme} from '@mui/material';
import './styles.css';
import {SignInPage} from './SignInPage';
import {PhotoBrowser} from './PhotoBrowser';
import LiveComparison, {type ConfirmedMatch, type Matches} from './LiveComparison';
import {ResearchCredits} from './ResearchCredits';

const qc = new QueryClient();
let csrfToken='';
let currentOrg='';
type Identity={mode:string;email:string;org_id:string;csrf:string;organizations:{id:string;name:string}[]};
const theme = createTheme({
 palette:{primary:{main:'#315a46'},background:{default:'#f5f6f3'},text:{primary:'#24352b',secondary:'#5b665f'}},
 shape:{borderRadius:8},
 typography:{fontFamily:'Inter, system-ui, sans-serif',fontSize:14,button:{textTransform:'none',fontWeight:600}},
 components:{
  MuiButton:{defaultProps:{size:'small',disableElevation:true},styleOverrides:{root:{minHeight:36}}},
  MuiTab:{styleOverrides:{root:{textTransform:'none',minHeight:44,fontWeight:600}}},
  MuiTabs:{styleOverrides:{root:{minHeight:44}}},
  MuiCard:{defaultProps:{variant:'outlined'}},
  MuiAlert:{styleOverrides:{root:{padding:'2px 12px'}}},
  MuiSelect:{defaultProps:{size:'small'}}
 }
});
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
  const r=await fetch(path,{method,headers:{...(body instanceof FormData?{}:{'Content-Type':'application/json'}),'X-CSRF-Token':csrfToken,'X-Organization-ID':currentOrg},body:body instanceof FormData?body:body===undefined?undefined:JSON.stringify(body)});
  if(r.status===401&&path.startsWith('/api/')){window.location.reload();throw new Error('Session expired');}
  if(r.status===409&&path.startsWith('/api/')){const message=await r.text();if(message.includes('Organization changed'))window.location.reload();throw new Error(message);}
  if(!r.ok) throw new Error((await r.text()) || r.statusText); return r.json();
}
type Bear={id:string;name:string|null;thumbnail_url?:string|null;photo_count?:number};
type Candidate={bear_id:string;name:string|null;reference_id:string;cosine:number};
type Head={id:string;index:number;box:number[];crop_url:string;recognition_state:string;review_state:string;bear_id:string|null;error:string|null;suggestions:{id:string;created_at:string;gallery_revision:number;candidates:Candidate[]}[]};
type Photo={id:string;filename:string;image_url:string;thumbnail_url:string;width:number;height:number;detection_state:string;pipeline:string;status_label?:string;created_at?:string;bear_ids?:string[]};
type Detail=Photo&{heads:Head[];jobs:{id:string;stage:string;state:string;error:string|null;attempts:number}[]};
type DeleteTarget={kind:'photo'|'bear';id:string;label:string};
const label=(b:Bear)=>b.name||`Unknown bear · ${b.id.slice(0,8)}`;
function App({identity}:{identity:Identity}){
 const [matchNotice,setMatchNotice]=useState<{confirmation:ConfirmedMatch;undone:boolean}|null>(null);
 const [comparison,setComparison]=useState<{headId:string;filename:string;initialMatchId?:string}|null>(null);
 const [tab,setTab]=useState(0),[selected,setSelected]=useState(''),[index,setIndex]=useState(0),[error,setError]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const [pendingUploads,setPendingUploads]=useState<{name:string;url:string}[]>([]);
 const [uploadCount,setUploadCount]=useState(0),[noticeSeverity,setNoticeSeverity]=useState<'success'|'warning'|'error'>('success');
 const [bearChoice,setBearChoice]=useState(''),[dialog,setDialog]=useState<'create'|'rename'|null>(null),[name,setName]=useState(''),[bearView,setBearView]=useState(''),[creditsOpen,setCreditsOpen]=useState(false);
 const [pendingDelete,setPendingDelete]=useState<DeleteTarget|null>(null);
 const health=useQuery({queryKey:[identity.org_id,'health'],queryFn:()=>api<{pipeline:string;commit:string;environment:string;auto_recognize?:boolean}>('/api/status')});
 const photos=useQuery({queryKey:[identity.org_id,'photos'],queryFn:()=>api<Photo[]>('/api/photos'),refetchInterval:3000});
 const bears=useQuery({queryKey:[identity.org_id,'bears'],queryFn:()=>api<Bear[]>('/api/bears')});
 const detail=useQuery({queryKey:[identity.org_id,'photo',selected],queryFn:()=>api<Detail>('/api/photos/'+selected),enabled:!!selected,refetchInterval:2000});
 const refs=useQuery({queryKey:[identity.org_id,'refs',bearView],queryFn:()=>api<Head[]>(`/api/bears/${bearView}/references`),enabled:!!bearView});
 const head=detail.data?.heads[index];
 const viewedBear=bears.data?.find(b=>b.id===bearView);
 const similar=useQuery({queryKey:[identity.org_id,'comparison',head?.id],queryFn:()=>api<Matches>(`/api/heads/${head!.id}/matches`),enabled:!!head&&head.recognition_state==='complete'&&!['ignored','unusable'].includes(head.review_state)&&!comparison,refetchInterval:comparison?false:5000});
 const history=useQuery({queryKey:[identity.org_id,'history',head?.id],queryFn:()=>api<{id:string;state:string;bear_id:string|null;created_at:string}[]>(`/api/heads/${head!.id}/history`),enabled:!!head});
 async function act(fn:()=>Promise<unknown>,lock=true){setError('');if(lock)setBusy(true);try{await fn();await qc.invalidateQueries();}catch(e){setError(String(e));}finally{if(lock)setBusy(false);}}
 async function undoComparison(){
  if(!matchNotice||matchNotice.undone)return;
  const receipt=matchNotice.confirmation;
  await act(async()=>{await api(`/api/heads/${receipt.headId}/undo-match`,'POST',receipt.undo);setMatchNotice(current=>current?.confirmation===receipt?{...current,undone:true}:current);});
 }
 async function removeTarget(){
  const target=pendingDelete;if(!target)return;
  await act(async()=>{
   setNoticeSeverity('success');
   if(target.kind==='photo'){
    await api(`/api/photos/${target.id}`,'DELETE');
    setSelected(current=>current===target.id?'':current);setIndex(0);
    setNotice(`Deleted photo: ${target.label}`);
   }else{
    await api(`/api/bears/${target.id}`,'DELETE');
    setBearView(current=>current===target.id?'':current);setBearChoice(current=>current===target.id?'':current);
    setNotice(`Deleted bear: ${target.label}`);
   }
   setPendingDelete(null);
  });
 }
 function review(state:string,bear_id?:string){if(head)void act(()=>api(`/api/heads/${head.id}/review`,'POST',{state,bear_id:bear_id||null}));}
 const recognizing=!!detail.data?.heads.some(h=>['queued','running'].includes(h.recognition_state));
 const headRecognizing=!!head&&['queued','running'].includes(head.recognition_state);
 const currentError=error||String(photos.error||detail.error||bears.error||health.error||'');
 return <>
 <div style={{display:comparison?'none':'contents'}}>
  <AppBar position="static" elevation={0} color="transparent" sx={{background:'#fff',borderBottom:'1px solid #dce2dc'}}>
<Toolbar variant="dense" sx={{gap:2,minHeight:64}}>
    <div className="portal-brand">
     <img className="portal-brand-mark" src="/bear.svg" width="42" height="42" alt=""/>
     <Typography component="h1" variant="h6" sx={{fontWeight:800,letterSpacing:'-0.6px',color:'primary.main',whiteSpace:'nowrap'}}>Only Bears</Typography>
    </div>
    <Select size="small" value={identity.org_id} disabled={busy||uploadCount>0||identity.organizations.length<2} inputProps={{"aria-label":"Organization"}} onChange={e=>void act(async()=>{await api("/api/session/organization","POST",{org_id:e.target.value});qc.clear();window.location.reload();})}>{identity.organizations.map(o=><MenuItem key={o.id} value={o.id}>{o.name}</MenuItem>)}</Select>
    {identity.mode==="google"&&<Button onClick={()=>void act(async()=>{await api("/api/session/logout","POST");qc.clear();window.location.reload();})}>Sign out</Button>}
    <Chip size="small" variant="outlined" label={!health.data?'Connecting':health.data.pipeline.startsWith('mock')?'Mock inference':health.data.environment==='aws'?'AWS · CPU':'Local · CPU'}/>
   </Toolbar>
  </AppBar>
  <Container className="app-content" maxWidth={false} sx={{py:2}}>
   <Stack className="workspace-stack" spacing={2}>
    {currentError&&<Alert severity="error" onClose={()=>setError('')}>{currentError}</Alert>}
    {matchNotice&&<Alert severity="success" onClose={()=>setMatchNotice(null)} action={!matchNotice.undone?<Button disabled={busy} onClick={()=>void undoComparison()}>Undo</Button>:undefined}>{matchNotice.undone?'Previous identity restored':'Identity saved'} · {matchNotice.confirmation.filename}</Alert>}
    {notice&&<Alert severity={noticeSeverity} onClose={()=>setNotice('')}>{notice}</Alert>}
    <div className="workspace-toolbar">
     <Tabs value={tab} onChange={(_,v)=>setTab(v)} aria-label="Collection views">
      <Tab label="Photos & review"/><Tab label="Bears"/>
     </Tabs>
     {tab===0&&<Button variant="contained" component="label" disabled={uploadCount>0} aria-busy={uploadCount>0} startIcon={uploadCount>0?<CircularProgress size={16} color="inherit" aria-label="Uploading photos"/>:undefined}>
      {uploadCount>0?`Uploading ${uploadCount} photo${uploadCount===1?'':'s'}…`:'Upload photos'}
      <input hidden multiple type="file" accept="image/jpeg,image/png" onChange={e=>{
       const files=Array.from(e.target.files||[]);e.target.value='';if(!files.length)return;
       if(files.some(f=>f.size>25*1024*1024)){setError('Each photo must be 25 MiB or smaller.');return;}
       if(files.length>20){setError('Select up to 20 photos at once.');return;}
       setNotice('');setUploadCount(files.length);
       const pending=files.map(f=>({name:f.name,url:URL.createObjectURL(f)}));setPendingUploads(pending);
       void act(async()=>{
        const form=new FormData();files.forEach(f=>form.append('files',f));
        const result=await api<{photos:(Photo&{error?:string;duplicate?:boolean})[]}>('/api/photos','POST',form);
        const failures=result.photos.filter(p=>p.error).length;
        setNoticeSeverity(failures===0?'success':failures===result.photos.length?'error':'warning');
        setNotice(result.photos.map(p=>`${p.filename}: ${p.error||(p.duplicate?'already uploaded':'saved')}`).join('; '));
        const first=result.photos.find(p=>p.id);if(first&&!selected){setSelected(current=>current||first.id);}
       },false).finally(()=>{setUploadCount(0);setPendingUploads([]);pending.forEach(p=>URL.revokeObjectURL(p.url));});
      }}/>
     </Button>}
    </div>
    {health.data?.pipeline.startsWith('mock')&&<Typography variant="body2" color="text.secondary">Test-only mock results · synthetic and separate from real inference.</Typography>}
    {tab===0?<div className="photo-workspace">
     <PhotoBrowser photos={photos.data||[]} bears={bears.data||[]} selected={selected} onSelect={id=>{setSelected(id);setIndex(0);setBearChoice('');}} pending={pendingUploads} loading={photos.isPending}/>
     {!selected&&<div className="empty-state"><Typography component="h2" variant="h6">Select a photo to review</Typography><Typography color="text.secondary">Review detected heads, then compare similar sightings.</Typography></div>}
     {selected&&detail.isPending&&<p className="muted">Loading photo…</p>}
     {detail.data&&<section className="photo-detail" aria-label="Photo review">
      <div className="photo-heading">
       <div><Typography component="h2" variant="h6" sx={{overflowWrap:'anywhere',fontSize:'1.05rem',fontWeight:600}}>{detail.data.filename}</Typography>
       <Typography variant="body2" color="text.secondary">{detail.data.detection_state==='complete'?(detail.data.heads.length?`${detail.data.heads.length} detected head${detail.data.heads.length===1?'':'s'} · select a numbered box to review`:'No head detected'):detail.data.detection_state==='failed'?'Detection failed':'Detecting heads…'}</Typography></div>
       <Button color="error" disabled={busy} onClick={()=>setPendingDelete({kind:'photo',id:detail.data!.id,label:detail.data!.filename})}>Delete photo</Button>
      </div>
      <div className="review-grid">
       <div className="photo-column">
        <div className="photo-stage">
         <div className="photo-canvas" style={{width:`min(100%, ${360*detail.data.width/detail.data.height}px)`}}>
          <img src={detail.data.image_url} alt="Oriented photo preview"/>
          {detail.data.heads.map((h,i)=><button type="button" className="head-box" key={h.id} aria-label={`Select head ${i+1}`} aria-pressed={i===index} onClick={()=>{setIndex(i);setBearChoice('');}} style={{left:`${100*h.box[0]/detail.data!.width}%`,top:`${100*h.box[1]/detail.data!.height}%`,width:`${100*(h.box[2]-h.box[0])/detail.data!.width}%`,height:`${100*(h.box[3]-h.box[1])/detail.data!.height}%`}}><span>{i+1}</span></button>)}
         </div>
        </div>
        {!!detail.data.heads.length&&health.data&&<div className="recognition-bar">
         <Typography variant="body2" color="text.secondary">{health.data.auto_recognize===false?'Review the detected heads, then run recognition on the eligible sightings.':'Detected heads are recognized automatically. Review matches and confirm identities below.'}</Typography>
         {health.data.auto_recognize===false&&<Button startIcon={recognizing?<CircularProgress size={16} color="inherit"/>:undefined} aria-busy={recognizing} disabled={busy||recognizing||!detail.data.heads.some(h=>['not_requested','failed'].includes(h.recognition_state)&&!['ignored','unusable'].includes(h.review_state))} variant="contained" onClick={()=>act(()=>api(`/api/photos/${selected}/recognize`,'POST'))}>{recognizing?'Recognizing…':'Run recognition'}</Button>}
        </div>}
        {detail.data.jobs.filter(j=>j.error&&j.state!=='superseded'&&!(j.stage==='detection'&&detail.data.detection_state==='complete')).map(j=><Alert key={j.id} severity={j.state==='failed'?'error':'warning'}>{j.stage}: {j.error} (attempts: {j.attempts}, {j.state}) {j.state==='failed'&&j.stage==='detection'&&<Button disabled={busy} onClick={()=>act(()=>api(`/api/jobs/${j.id}/retry`,'POST'))}>Retry detection</Button>}</Alert>)}
       </div>
       {head&&<Card className="review-panel"><CardContent sx={{p:2,'&:last-child':{pb:2}}}><Stack spacing={1.5}>
        <div className="head-navigation"><Button disabled={index===0} onClick={()=>{setIndex(index-1);setBearChoice('');}}>Previous</Button><Typography component="h3" variant="subtitle2">Head {index+1} of {detail.data.heads.length}</Typography><Button disabled={index===detail.data.heads.length-1} onClick={()=>{setIndex(index+1);setBearChoice('');}}>Next</Button></div>
        <div className="head-summary">
         <img src={head.crop_url} alt={`Head ${index+1}`}/>
         <div><Chip size="small" variant="outlined" label={head.review_state.replaceAll('_',' ')}/><Typography variant="body2" color="text.secondary" sx={{mt:1}}>Recognition: {head.recognition_state==='not_requested'?'not run':head.recognition_state.replaceAll('_',' ')}</Typography>{head.bear_id&&<Typography variant="body2" sx={{mt:.5,overflowWrap:'anywhere'}}>{label(bears.data?.find(b=>b.id===head.bear_id)||{id:head.bear_id,name:null})}</Typography>}</div>
        </div>
        {headRecognizing&&<div className="recognition-status" role="status"><CircularProgress size={24}/><div><strong>{head.recognition_state==='queued'?'Recognition queued':'Recognizing this bear…'}</strong><p>{head.recognition_state==='queued'?'Waiting for the next available worker. You can keep reviewing.':'Comparing this head with identified and unidentified sightings. Results appear here automatically.'}</p></div></div>}
        {head.error&&<Alert severity="error" action={!['ignored','unusable'].includes(head.review_state)?<Button disabled={busy} onClick={()=>act(()=>api(`/api/photos/${selected}/recognize`,'POST'))}>Retry recognition</Button>:undefined}>{head.error}</Alert>}
        <Stack direction="row" spacing={.5} useFlexGap flexWrap="wrap">{['unresolved','ignored','unusable'].map(state=><Button key={state} disabled={busy} onClick={()=>review(state)}>{state==='unresolved'?(['ignored','unusable'].includes(head.review_state)?'Restore as unidentified':head.bear_id?'Remove identity':'Leave unidentified'):state==='ignored'?'Ignore subject':'Mark unusable'}</Button>)}</Stack>
        {head.recognition_state==='complete'&&<div className="panel-section">
         <div className="section-heading"><Typography component="h3" variant="subtitle2">Similar sightings</Typography></div>
         {['ignored','unusable'].includes(head.review_state)?<Typography variant="body2" color="text.secondary">Restore this sighting as unidentified to compare matches.</Typography>:<>
          <Typography variant="caption" color="text.secondary">Top 10 photos · highest similarity first · similarity is not identity probability.</Typography>
          {similar.isPending&&<Typography variant="body2" role="status">Loading matches…</Typography>}
          {similar.error&&<Alert severity="error" action={<Button onClick={()=>void similar.refetch()}>Retry</Button>}>Unable to load similar sightings.</Alert>}
          {!similar.isPending&&!similar.error&&!similar.data?.candidates.length&&<Typography variant="body2">No similar sightings yet.</Typography>}
          <div className="candidate-list" aria-label="Similar sightings">{[...(similar.data?.candidates||[])].sort((a,b)=>b.similarity-a.similarity).map(candidate=><div className="candidate-row" key={candidate.id}>
           <img src={candidate.photos[0]?.src} alt={candidate.label} loading="lazy"/>
           <div><Typography variant="body2" sx={{fontWeight:600,overflowWrap:'anywhere'}}>{candidate.label}</Typography><Typography variant="caption" color="text.secondary">Similarity {candidate.similarity.toFixed(3)}</Typography></div>
           <Button disabled={busy||!!similar.error} aria-label={`Compare ${candidate.label}`} onClick={()=>setComparison({headId:head.id,filename:detail.data!.filename,initialMatchId:candidate.id})}>Compare</Button>
          </div>)}</div>
         </>}
        </div>}
        <div className="panel-section">
         <Typography component="h3" variant="subtitle2" sx={{mb:1}}>Assign identity</Typography>
         <div className="assign-row"><Select displayEmpty value={bearChoice} inputProps={{'aria-label':'Choose an existing bear'}} onChange={e=>setBearChoice(e.target.value)} sx={{minWidth:0,flex:1}}><MenuItem value="">Choose existing bear</MenuItem>{bears.data?.map(b=><MenuItem key={b.id} value={b.id}>{label(b)}</MenuItem>)}</Select><Button disabled={busy||!bearChoice} variant="outlined" onClick={()=>review('confirmed',bearChoice)}>Assign</Button></div>
         <Button sx={{mt:.5}} disabled={busy} onClick={()=>{setName('');setDialog('create');}}>Create new bear & assign</Button>
        </div>
        {!!history.data?.length&&<details className="compact-details" key={head.id}><summary>Review history ({history.data.length})</summary>{history.data.map(r=><Typography variant="caption" display="block" key={r.id}>{new Date(r.created_at).toLocaleString()} · {r.state}{r.bear_id?` · ${r.bear_id.slice(0,8)}`:''}</Typography>)}</details>}
       </Stack></CardContent></Card>}
      </div>
     </section>}
    </div>:<div className="photo-workspace">
     <aside className="collection-list" aria-label="Bears"><div className="section-label">Bears <span>{bears.data?.length??0}</span></div><div className="collection-items">
       {bears.data?.map(b=><button type="button" className="collection-item" key={b.id} aria-current={bearView===b.id?'true':undefined} onClick={()=>setBearView(b.id)}><span className="bear-avatar" aria-hidden="true">{b.thumbnail_url?<img src={b.thumbnail_url} alt="" loading="lazy"/>:'—'}</span><span className="item-name">{label(b)}</span></button>)}</div>{!bears.data?.length&&<p className="muted">Create a bear while reviewing a head.</p>}</aside>
     {bearView?<section className="reference-panel"><div className="section-heading"><Typography component="h2" variant="h6" sx={{overflowWrap:'anywhere'}}>{label(viewedBear||{id:bearView,name:null})}</Typography><Stack direction="row" spacing={1}><Button onClick={()=>{setName(viewedBear?.name||'');setDialog('rename');}}>Edit name</Button><Tooltip title={(viewedBear?.photo_count||0)>0?`Reassign or remove this bear from ${viewedBear!.photo_count} associated photo${viewedBear!.photo_count===1?'':'s'} before deleting it.`:''}><span><Button color="error" disabled={busy||(viewedBear?.photo_count||0)>0} onClick={()=>setPendingDelete({kind:'bear',id:bearView,label:label(viewedBear||{id:bearView,name:null})})}>Delete bear</Button></span></Tooltip></Stack></div><Typography variant="body2" color="text.secondary">Confirmed usable heads with valid embeddings become references.</Typography><div className="reference-grid">{refs.data?.map((h,i)=><img key={h.id} src={h.crop_url} alt={`Confirmed reference ${i+1}`}/>)}</div>{refs.error&&<Alert severity="error">{String(refs.error)}</Alert>}{refs.isPending?<Typography color="text.secondary">Loading references…</Typography>:!refs.data?.length&&!refs.error&&<Typography color="text.secondary">No eligible references for this bear yet.</Typography>}</section>:<div className="empty-state"><Typography component="h2" variant="h6">Select a bear to view references</Typography><Typography color="text.secondary">Bear identities stay the same when names change.</Typography></div>}
    </div>}
    <div className="workspace-footer"><details className="compact-details workspace-help"><summary>How review works</summary><p>Upload JPEG or PNG photos. {health.data?.auto_recognize===false?'Detection runs automatically; review each detected head, then run recognition and confirm identities.':'Detection and recognition run automatically; review each head and confirm its identity.'} Confirming a usable head with a valid embedding creates a reference for later matching.</p><p>Leave uncertain heads unresolved. Matching quality is experimental; no identity is assigned automatically. Head detection uses oriented originals with no body detector or crop margin. One shared collection; bear IDs stay stable when names change.</p></details><Button className="credits-link" onClick={()=>setCreditsOpen(true)}>Research & credits</Button></div>
   </Stack>
  </Container>
  <Dialog open={!!dialog} onClose={()=>setDialog(null)} fullWidth maxWidth="xs"><DialogTitle>{dialog==='create'?'Create a distinct bear':'Edit display name'}</DialogTitle><DialogContent><TextField fullWidth autoFocus label="Display name (optional)" value={name} inputProps={{maxLength:120}} onChange={e=>setName(e.target.value)} sx={{mt:1}}/><Typography variant="body2" color="text.secondary" sx={{mt:1}}>Leave blank to create an unknown bear. Each unknown bear remains a distinct identity.</Typography></DialogContent><DialogActions><Button onClick={()=>setDialog(null)}>Cancel</Button><Button disabled={busy} onClick={()=>act(async()=>{if(dialog==='create'){const b=await api<Bear>('/api/bears','POST',{name:name||null});await api(`/api/heads/${head!.id}/review`,'POST',{state:'confirmed',bear_id:b.id});}else await api(`/api/bears/${bearView}`,'PATCH',{name:name||null});setDialog(null);})}>Save</Button></DialogActions></Dialog>
  <Dialog open={!!pendingDelete} onClose={()=>{if(!busy)setPendingDelete(null);}} fullWidth maxWidth="xs"><DialogTitle>{pendingDelete?.kind==='photo'?'Delete this photo?':'Delete this bear?'}</DialogTitle><DialogContent>{pendingDelete?.kind==='photo'?<Typography>This permanently deletes <strong>{pendingDelete.label}</strong>, its detected heads, and its recognition and review history.</Typography>:<Typography>This permanently deletes <strong>{pendingDelete?.label}</strong>. Only bears with no associated photos can be deleted.</Typography>}</DialogContent><DialogActions><Button disabled={busy} onClick={()=>setPendingDelete(null)}>Cancel</Button><Button color="error" variant="contained" disabled={busy} onClick={()=>void removeTarget()}>{busy?'Deleting…':'Delete'}</Button></DialogActions></Dialog>
  <Dialog open={creditsOpen} onClose={()=>setCreditsOpen(false)} fullWidth maxWidth="sm"><DialogTitle>Research & credits</DialogTitle><DialogContent><ResearchCredits/></DialogContent><DialogActions><Button onClick={()=>setCreditsOpen(false)}>Close</Button></DialogActions></Dialog>
 </div>
 {comparison&&<LiveComparison key={comparison.headId} {...comparison} orgId={identity.org_id} api={api} bears={bears.data||[]} onBack={()=>setComparison(null)} onConfirmed={result=>{setError('');setMatchNotice({confirmation:result,undone:false});setComparison(null);void qc.invalidateQueries();}}/>}
 </>;
}
function AccountGate(){
 const identity=useQuery({queryKey:['identity'],queryFn:async()=>{const r=await fetch('/auth/me');if(r.status===401||r.status===403)return null;if(!r.ok)throw new Error('Unable to check sign-in');return r.json() as Promise<Identity>;},retry:false,refetchOnWindowFocus:true});
 if(identity.isPending)return <Container sx={{py:8}}><CircularProgress aria-label="Checking sign-in"/></Container>;
 if(identity.error)return <Container sx={{py:8}}><Alert severity="error">Cannot connect. Please refresh to try again.</Alert></Container>;
 if(!identity.data)return <SignInPage/>;
 csrfToken=identity.data.csrf;currentOrg=identity.data.org_id;
 return <App key={identity.data.org_id} identity={identity.data}/>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={qc}><ThemeProvider theme={theme}><CssBaseline/><AccountGate/></ThemeProvider></QueryClientProvider></React.StrictMode>);
