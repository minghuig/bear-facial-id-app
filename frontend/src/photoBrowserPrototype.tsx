import React,{useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {CssBaseline,ThemeProvider,createTheme} from '@mui/material';
import {PhotoBrowser} from './PhotoBrowser';
import './styles.css';

const bears=[{id:'hazel',name:'Hazel'},{id:'juniper',name:'Juniper'},{id:'cedar',name:'Cedar'},{id:'unnamed',name:null}];
const statuses=['Ready to Review','Reviewed · 1 confirmed','Partially reviewed (1/2) · 1 confirmed','Recognizing Bears…','Detection failed','No bears detected','Reviewed · 1 unidentified'];
const fallback='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80"><rect width="100" height="80" fill="#dce2d6"/><text x="50" y="44" text-anchor="middle" font-size="12" fill="#315a46">Photo</text></svg>');
function Prototype(){
 const [images,setImages]=useState<{thumbnail_url:string;image_url:string}[]>([]),[selected,setSelected]=useState('0');
 useEffect(()=>{fetch('/api/photos').then(r=>r.ok?r.json():[]).then(setImages).catch(()=>{});},[]);
 const photos=Array.from({length:500},(_,i)=>({id:String(i),filename:`Trail camera ${String(i+1).padStart(4,'0')}.jpg`,created_at:new Date(Date.UTC(2026,8,14)-i*3600000*8).toISOString(),detection_state:'complete',status_label:statuses[i%7],bear_ids:[1,2].includes(i%7)?[bears[i%4].id]:[],thumbnail_url:images[i%Math.max(images.length,1)]?.thumbnail_url||fallback}));
 const photo=photos[Number(selected)];
 return <><header style={{padding:'16px 24px',background:'white',borderBottom:'1px solid #dce2dc'}}><strong>Only Bears · Photo library prototype</strong><p style={{margin:'4px 0 0',fontSize:13,color:'#5b665f'}}>500 sample records · synthetic dates, statuses and identities · existing photos reused for previews</p></header><main className="app-content" style={{padding:20}}><div className="photo-workspace"><PhotoBrowser photos={photos} bears={bears} selected={selected} onSelect={setSelected} pending={[]} loading={false}/><section className="photo-detail"><h2>{photo.filename}</h2><p>{photo.status_label}</p><div className="photo-stage"><img style={{maxWidth:'100%',maxHeight:'55vh',objectFit:'contain'}} src={images[Number(selected)%Math.max(images.length,1)]?.image_url||fallback} alt="Selected sample bear photo"/></div><p className="muted">Try combining “Needs review” with a bear, change the upload order, or browse the next page. Your selected photo stays open.</p></section></div></main></>;
}
createRoot(document.getElementById('root')!).render(<ThemeProvider theme={createTheme({palette:{primary:{main:'#315a46'},background:{default:'#f5f6f3'}},typography:{fontFamily:'Inter, system-ui, sans-serif',button:{textTransform:'none'}}})}><CssBaseline/><Prototype/></ThemeProvider>);
