import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import {QueryClient, QueryClientProvider, useQuery} from '@tanstack/react-query';
import {Alert, AppBar, Button, Card, CardContent, Chip, CircularProgress, Container, CssBaseline, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Select, Stack, Tab, Tabs, TextField, ThemeProvider, Toolbar, Typography, createTheme} from '@mui/material';
import './styles.css';

const qc = new QueryClient();
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
  const r=await fetch(path,{method,headers:body instanceof FormData?{}:{'Content-Type':'application/json'},body:body instanceof FormData?body:body===undefined?undefined:JSON.stringify(body)});
  if(!r.ok) throw new Error((await r.text()) || r.statusText); return r.json();
}
type Bear={id:string;name:string|null};
type Candidate={bear_id:string;name:string|null;reference_id:string;cosine:number};
type Head={id:string;index:number;box:number[];crop_url:string;recognition_state:string;review_state:string;bear_id:string|null;error:string|null;suggestions:{id:string;created_at:string;gallery_revision:number;candidates:Candidate[]}[]};
type Photo={id:string;filename:string;image_url:string;width:number;height:number;detection_state:string;pipeline:string};
type Detail=Photo&{heads:Head[];jobs:{id:string;stage:string;state:string;error:string|null;attempts:number}[]};
const label=(b:Bear)=>b.name||`Unnamed bear · ${b.id.slice(0,8)}`;
function App(){
 const [tab,setTab]=useState(0),[selected,setSelected]=useState(''),[index,setIndex]=useState(0),[error,setError]=useState(''),[busy,setBusy]=useState(false),[notice,setNotice]=useState('');
 const [uploadCount,setUploadCount]=useState(0),[noticeSeverity,setNoticeSeverity]=useState<'success'|'warning'|'error'>('success');
 const [bearChoice,setBearChoice]=useState(''),[dialog,setDialog]=useState<'create'|'rename'|null>(null),[name,setName]=useState(''),[bearView,setBearView]=useState('');
 const health=useQuery({queryKey:['health'],queryFn:()=>api<{pipeline:string;commit:string;environment:string}>('/health')});
 const photos=useQuery({queryKey:['photos'],queryFn:()=>api<Photo[]>('/api/photos'),refetchInterval:3000});
 const bears=useQuery({queryKey:['bears'],queryFn:()=>api<Bear[]>('/api/bears')});
 const detail=useQuery({queryKey:['photo',selected],queryFn:()=>api<Detail>('/api/photos/'+selected),enabled:!!selected,refetchInterval:2000});
 const refs=useQuery({queryKey:['refs',bearView],queryFn:()=>api<Head[]>(`/api/bears/${bearView}/references`),enabled:!!bearView});
 const head=detail.data?.heads[index];
 const history=useQuery({queryKey:['history',head?.id],queryFn:()=>api<{id:string;state:string;bear_id:string|null;created_at:string}[]>(`/api/heads/${head!.id}/history`),enabled:!!head});
 async function act(fn:()=>Promise<unknown>){setError('');setBusy(true);try{await fn();await qc.invalidateQueries();}catch(e){setError(String(e));}finally{setBusy(false);}}
 function review(state:string,bear_id?:string){if(head)void act(()=>api(`/api/heads/${head.id}/review`,'POST',{state,bear_id:bear_id||null}));}
 const currentError=error||String(photos.error||detail.error||bears.error||health.error||'');
 return <>
  <AppBar position="static" elevation={0} color="transparent" sx={{background:'#fff',borderBottom:'1px solid #dce2dc'}}>
   <Toolbar variant="dense" sx={{gap:2,minHeight:56}}>
    <Typography component="h1" variant="h6" sx={{flex:1,fontWeight:700}}>Only Bears</Typography>
    <Chip size="small" variant="outlined" label={!health.data?'Connecting':health.data.pipeline.startsWith('mock')?'Mock inference':health.data.environment==='aws'?'AWS · CPU':'Local · CPU'}/>
   </Toolbar>
  </AppBar>
  <Container maxWidth="xl" sx={{py:2}}>
   <Stack spacing={2}>
    {currentError&&<Alert severity="error" onClose={()=>setError('')}>{currentError}</Alert>}
    {notice&&<Alert severity={noticeSeverity} onClose={()=>setNotice('')}>{notice}</Alert>}
    <div className="workspace-toolbar">
     <Tabs value={tab} onChange={(_,v)=>setTab(v)} aria-label="Collection views">
      <Tab label="Photos & review"/><Tab label="Bears & references"/>
     </Tabs>
     {tab===0&&<Button variant="contained" component="label" disabled={busy} aria-busy={uploadCount>0} startIcon={uploadCount>0?<CircularProgress size={16} color="inherit" aria-label="Uploading photos"/>:undefined}>
      {uploadCount>0?`Uploading ${uploadCount} photo${uploadCount===1?'':'s'}…`:'Upload photos'}
      <input hidden multiple type="file" accept="image/jpeg,image/png" onChange={e=>{
       const files=Array.from(e.target.files||[]);e.target.value='';if(!files.length)return;
       if(files.length>20){setError('Select up to 20 photos at once.');return;}
       setNotice('');setUploadCount(files.length);
       void act(async()=>{
        const form=new FormData();files.forEach(f=>form.append('files',f));
        const result=await api<{photos:(Photo&{error?:string;duplicate?:boolean})[]}>('/api/photos','POST',form);
        const failures=result.photos.filter(p=>p.error).length;
        setNoticeSeverity(failures===0?'success':failures===result.photos.length?'error':'warning');
        setNotice(result.photos.map(p=>`${p.filename}: ${p.error||(p.duplicate?'already uploaded':'saved')}`).join('; '));
        const first=result.photos.find(p=>p.id);if(first){setSelected(first.id);setIndex(0);setBearChoice('');}
       }).finally(()=>setUploadCount(0));
      }}/>
     </Button>}
    </div>
    {health.data?.pipeline.startsWith('mock')&&<Typography variant="body2" color="text.secondary">Mock results for development · separate from real inference.</Typography>}
    {tab===0?<div className="photo-workspace">
     <aside className="collection-list" aria-label="Photos">
      <div className="section-label">Photos <span>{photos.data?.length??0}</span></div>
      <div className="collection-items">
       {photos.data?.map(p=><button type="button" key={p.id} className="collection-item" aria-current={selected===p.id?'true':undefined} onClick={()=>{setSelected(p.id);setIndex(0);setBearChoice('');}}>
        <img src={p.image_url} alt="" loading="lazy"/>
        <span className="item-copy"><span className="item-name" title={p.filename}>{p.filename}</span><span className="item-state">{p.detection_state==='complete'?'Ready to review':p.detection_state.replaceAll('_',' ')}</span></span>
       </button>)}
      </div>
      {!photos.data?.length&&<p className="muted">{photos.isPending?'Loading photos…':'Upload a JPEG or PNG to begin.'}</p>}
     </aside>
     {!selected&&<div className="empty-state"><Typography component="h2" variant="h6">Select a photo to review</Typography><Typography color="text.secondary">Review detected heads, then match against confirmed bears.</Typography></div>}
     {selected&&detail.isPending&&<p className="muted">Loading photo…</p>}
     {detail.data&&<section className="photo-detail" aria-label="Photo review">
      <div className="photo-heading">
       <Typography component="h2" variant="h6" sx={{overflowWrap:'anywhere',fontSize:'1.05rem',fontWeight:600}}>{detail.data.filename}</Typography>
       <Typography variant="body2" color="text.secondary">{detail.data.detection_state==='complete'?(detail.data.heads.length?`${detail.data.heads.length} detected head${detail.data.heads.length===1?'':'s'} · select a numbered box to review`:'No head detected'):detail.data.detection_state==='failed'?'Detection failed':'Detecting heads…'}</Typography>
      </div>
      <div className="review-grid">
       <div className="photo-column">
        <div className="photo-stage">
         <div className="photo-canvas" style={{width:`min(100%, ${360*detail.data.width/detail.data.height}px)`}}>
          <img src={detail.data.image_url} alt="Oriented original"/>
          {detail.data.heads.map((h,i)=><button type="button" className="head-box" key={h.id} aria-label={`Select head ${i+1}`} aria-pressed={i===index} onClick={()=>{setIndex(i);setBearChoice('');}} style={{left:`${100*h.box[0]/detail.data!.width}%`,top:`${100*h.box[1]/detail.data!.height}%`,width:`${100*(h.box[2]-h.box[0])/detail.data!.width}%`,height:`${100*(h.box[3]-h.box[1])/detail.data!.height}%`}}><span>{i+1}</span></button>)}
         </div>
        </div>
        {!!detail.data.heads.length&&<div className="recognition-bar">
         <Typography variant="body2" color="text.secondary">Ignore cubs or unusable crops first. Recognition runs only when requested.</Typography>
         <Button disabled={busy||!detail.data.heads.some(h=>['not_requested','failed'].includes(h.recognition_state)&&!['ignored','unusable'].includes(h.review_state))} variant="contained" onClick={()=>act(()=>api(`/api/photos/${selected}/recognize`,'POST'))}>Run recognition</Button>
        </div>}
        {detail.data.jobs.filter(j=>j.error&&j.state!=='superseded').map(j=><Alert key={j.id} severity={j.state==='failed'?'error':'warning'}>{j.stage}: {j.error} (attempts: {j.attempts}, {j.state}) {j.state==='failed'&&j.stage==='detection'&&<Button disabled={busy} onClick={()=>act(()=>api(`/api/jobs/${j.id}/retry`,'POST'))}>Retry detection</Button>}</Alert>)}
       </div>
       {head&&<Card className="review-panel"><CardContent sx={{p:2,'&:last-child':{pb:2}}}><Stack spacing={1.5}>
        <div className="head-navigation"><Button disabled={index===0} onClick={()=>{setIndex(index-1);setBearChoice('');}}>Previous</Button><Typography component="h3" variant="subtitle2">Head {index+1} of {detail.data.heads.length}</Typography><Button disabled={index===detail.data.heads.length-1} onClick={()=>{setIndex(index+1);setBearChoice('');}}>Next</Button></div>
        <div className="head-summary">
         <img src={head.crop_url} alt={`Head ${index+1}`}/>
         <div><Chip size="small" variant="outlined" label={head.review_state.replaceAll('_',' ')}/><Typography variant="body2" color="text.secondary" sx={{mt:1}}>Recognition: {head.recognition_state==='not_requested'?'not run':head.recognition_state.replaceAll('_',' ')}</Typography>{head.bear_id&&<Typography variant="body2" sx={{mt:.5,overflowWrap:'anywhere'}}>{label(bears.data?.find(b=>b.id===head.bear_id)||{id:head.bear_id,name:null})}</Typography>}</div>
        </div>
        {head.error&&<Alert severity="error">{head.error}. Run recognition again to retry this eligible head.</Alert>}
        <Stack direction="row" spacing={.5} useFlexGap flexWrap="wrap">{['unresolved','ignored','unusable'].map(state=><Button key={state} disabled={busy} onClick={()=>review(state)}>{state==='unresolved'?'Leave unresolved':state==='ignored'?'Ignore subject':'Mark unusable'}</Button>)}</Stack>
        {head.recognition_state==='complete'&&<div className="panel-section">
         <div className="section-heading"><Typography component="h3" variant="subtitle2">Candidate bears</Typography><Button disabled={busy} onClick={()=>act(()=>api(`/api/heads/${head.id}/refresh`,'POST'))}>Refresh</Button></div>
         <Typography variant="body2" color="text.secondary">Similarity is not identity probability.</Typography>
         {!head.suggestions[0]?.candidates.length&&<Typography variant="body2" sx={{py:1}}>No eligible references. Assign a bear below or leave unresolved.</Typography>}
         <div className="candidate-list">{head.suggestions[0]?.candidates.map(c=><div className="candidate-row" key={c.bear_id}>
          <img src={`/api/heads/${c.reference_id}/image`} alt="Supporting confirmed reference"/>
          <div><Typography variant="body2" sx={{fontWeight:600,overflowWrap:'anywhere'}}>{label({id:c.bear_id,name:c.name})}</Typography><Typography variant="caption" color="text.secondary">Cosine {c.cosine.toFixed(4)}</Typography></div>
          <Button disabled={busy} onClick={()=>review('confirmed',c.bear_id)} aria-label={`Confirm ${label({id:c.bear_id,name:c.name})}`}>Confirm</Button>
         </div>)}</div>
         <details className="compact-details"><summary>About these matches</summary><p>Bears with more references may be favored. An empty candidate list does not establish a new individual.</p><p>Saved snapshot revision {head.suggestions[0]?.gallery_revision??'—'} · {head.suggestions.length} snapshot(s)</p></details>
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
     <aside className="collection-list" aria-label="Bears"><div className="section-label">Bears <span>{bears.data?.length??0}</span></div><div className="collection-items">{bears.data?.map(b=><button type="button" className="collection-item" key={b.id} aria-current={bearView===b.id?'true':undefined} onClick={()=>setBearView(b.id)}><span className="bear-avatar" aria-hidden="true">{(b.name||'?').slice(0,1).toUpperCase()}</span><span className="item-name">{label(b)}</span></button>)}</div>{!bears.data?.length&&<p className="muted">Create a bear while reviewing a head.</p>}</aside>
     {bearView?<section className="reference-panel"><div className="section-heading"><Typography component="h2" variant="h6" sx={{overflowWrap:'anywhere'}}>{label(bears.data?.find(b=>b.id===bearView)||{id:bearView,name:null})}</Typography><Button onClick={()=>{setName(bears.data?.find(b=>b.id===bearView)?.name||'');setDialog('rename');}}>Edit name</Button></div><Typography variant="body2" color="text.secondary">Confirmed usable heads with valid embeddings become references.</Typography><div className="reference-grid">{refs.data?.map((h,i)=><img key={h.id} src={h.crop_url} alt={`Confirmed reference ${i+1}`}/>)}</div>{refs.error&&<Alert severity="error">{String(refs.error)}</Alert>}{refs.isPending?<Typography color="text.secondary">Loading references…</Typography>:!refs.data?.length&&!refs.error&&<Typography color="text.secondary">No eligible references for this bear yet.</Typography>}</section>:<div className="empty-state"><Typography component="h2" variant="h6">Select a bear to view references</Typography><Typography color="text.secondary">Bear identities stay the same when names change.</Typography></div>}
    </div>}
    <details className="compact-details workspace-help"><summary>How review works</summary><p>Upload JPEG or PNG photos, review each detected head, then run recognition on eligible heads. Confirming a usable head with a valid embedding creates a reference for later matching.</p><p>Leave uncertain heads unresolved. Matching quality is experimental; no identity is assigned automatically. Head detection uses oriented originals with no body detector or crop margin. One shared collection; bear IDs stay stable when names change.</p></details>
   </Stack>
  </Container>
  <Dialog open={!!dialog} onClose={()=>setDialog(null)} fullWidth maxWidth="xs"><DialogTitle>{dialog==='create'?'Create a distinct bear':'Edit display name'}</DialogTitle><DialogContent><TextField fullWidth autoFocus label="Display name (optional)" value={name} inputProps={{maxLength:120}} onChange={e=>setName(e.target.value)} sx={{mt:1}}/><Typography variant="body2" color="text.secondary" sx={{mt:1}}>Leave blank for an unnamed identity. “Unknown” is not a shared identity.</Typography></DialogContent><DialogActions><Button onClick={()=>setDialog(null)}>Cancel</Button><Button disabled={busy} onClick={()=>act(async()=>{if(dialog==='create'){const b=await api<Bear>('/api/bears','POST',{name:name||null});await api(`/api/heads/${head!.id}/review`,'POST',{state:'confirmed',bear_id:b.id});}else await api(`/api/bears/${bearView}`,'PATCH',{name:name||null});setDialog(null);})}>Save</Button></DialogActions></Dialog>
 </>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><QueryClientProvider client={qc}><ThemeProvider theme={theme}><CssBaseline/><App/></ThemeProvider></QueryClientProvider></React.StrictMode>);
