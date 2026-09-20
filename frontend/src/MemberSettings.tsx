import React, {useState} from 'react';
import {useQuery} from '@tanstack/react-query';
import {Alert, Button, Card, CardContent, Chip, CircularProgress, MenuItem, Stack, TextField, Typography} from '@mui/material';

type Membership = {org_id:string; email:string; status:'pending'|'active'; is_owner:boolean};
type Data = {organizations:{id:string;name:string}[]; memberships:Membership[]};
type Api = <T>(path:string, method?:string, body?:unknown)=>Promise<T>;

export function MemberSettings({api, currentOrg, localMode}:{api:Api;currentOrg:string;localMode:boolean}){
 const [orgId,setOrgId]=useState(currentOrg),[email,setEmail]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const [removing,setRemoving]=useState('');
 const members=useQuery({queryKey:['admin-memberships'],queryFn:()=>api<Data>('/api/admin/memberships')});

 async function invite(event:React.FormEvent){
  event.preventDefault();setBusy(true);setError('');setNotice('');
  try{
   const result=await api<Membership&{created:boolean}>('/api/admin/memberships','POST',{org_id:orgId,email:email.trim()});
   setNotice(result.created?(localMode?`Local test invitation added for ${result.email}.`:`Invitation added for ${result.email}. Share the app link with them.`):`${result.email} already has an invitation to this library.`);
   setEmail('');await members.refetch();
  }catch(e){setError(String(e));}finally{setBusy(false);}
 }

 async function remove(member:Membership){
  setBusy(true);setError('');setNotice('');
  try{
   await api('/api/admin/memberships','DELETE',{org_id:member.org_id,email:member.email});
   setNotice(`Removed ${member.email} from this library.`);setRemoving('');await members.refetch();
  }catch(e){setError(String(e));}finally{setBusy(false);}
 }

 return <section aria-label="Member settings">
  <Typography component="h2" variant="h6" sx={{mb:1}}>Member settings</Typography>
  {localMode&&<Alert severity="info" sx={{mb:2}}>Local test mode: changes here affect only this computer's database. People cannot sign in through this local preview.</Alert>}
  <Typography color="text.secondary" sx={{mb:2}}>Invite someone using their exact Google account email. Every member can view, edit, and delete items in the libraries they join. The app does not send invitation emails.</Typography>
  {error&&<Alert severity="error" onClose={()=>setError('')} sx={{mb:2}}>{error}</Alert>}
  {notice&&<Alert severity="success" onClose={()=>setNotice('')} sx={{mb:2}}>{notice}</Alert>}
  {members.isPending&&<CircularProgress aria-label="Loading members"/>}
  {members.error&&<Alert severity="error">Could not load members. <Button onClick={()=>void members.refetch()}>Retry</Button></Alert>}
  {members.data&&<>
   <Card sx={{mb:2}}><CardContent>
    <Typography component="h3" variant="subtitle1" sx={{fontWeight:700,mb:1}}>Add a member</Typography>
    <Stack component="form" onSubmit={e=>void invite(e)} direction={{xs:'column',sm:'row'}} spacing={1} alignItems={{sm:'center'}}>
     <TextField label="Google account email" type="email" required size="small" value={email} onChange={e=>setEmail(e.target.value)} disabled={busy} sx={{flex:2}}/>
     <TextField select label="Library" size="small" value={orgId} onChange={e=>setOrgId(e.target.value)} disabled={busy} sx={{flex:1,minWidth:150}}>
      {members.data.organizations.map(org=><MenuItem key={org.id} value={org.id}>{org.name}</MenuItem>)}
     </TextField>
     <Button type="submit" variant="contained" disabled={busy||!email.trim()||!orgId}>Add</Button>
    </Stack>
    <Typography variant="caption" color="text.secondary" display="block" sx={{mt:1}}>Gmail and Google Workspace addresses can claim invitations when they sign in. Google accounts with another provider's email are not supported by this screen yet.</Typography>
   </CardContent></Card>
   <Stack spacing={2}>{members.data.organizations.map(org=>{
    const rows=members.data.memberships.filter(member=>member.org_id===org.id);
    return <Card key={org.id}><CardContent>
     <Typography component="h3" variant="subtitle1" sx={{fontWeight:700,mb:1}}>{org.name} · {rows.length} {rows.length===1?'member':'members'}</Typography>
     {!rows.length&&<Typography color="text.secondary">No invitations yet.</Typography>}
     <Stack spacing={1}>{rows.map(member=>{
      const key=`${member.org_id}:${member.email}`;
      return <Stack key={key} direction={{xs:'column',sm:'row'}} spacing={1} alignItems={{sm:'center'}} justifyContent="space-between" sx={{py:.75,borderTop:'1px solid #e4e8e3'}}>
       <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap">
        <Typography sx={{overflowWrap:'anywhere'}}>{member.email}</Typography>
        <Chip size="small" variant="outlined" label={member.status==='active'?'Active':'Pending sign-in'}/>
        {member.is_owner&&<Chip size="small" label="Owner"/>}
       </Stack>
       {member.is_owner?null:removing===key?<Stack direction="row" spacing={1} alignItems="center">
        <Typography variant="body2">Remove access?</Typography>
        <Button color="error" disabled={busy} onClick={()=>void remove(member)}>Remove</Button>
        <Button disabled={busy} onClick={()=>setRemoving('')}>Cancel</Button>
       </Stack>:<Button color="error" disabled={busy} onClick={()=>setRemoving(key)}>Remove</Button>}
      </Stack>;
     })}</Stack>
    </CardContent></Card>;
   })}</Stack>
  </>}
 </section>;
}
