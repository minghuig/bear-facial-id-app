export type BrowserPhoto = {id:string; filename:string; created_at?:string; status_label?:string; detection_state?:string; bear_ids?:string[]};
export const statusOptions = [['all','All statuses'],['needs-review','Needs review'],['reviewed','Reviewed'],['processing','Processing'],['failed','Failed'],['empty','No bears detected']] as const;
export function statusGroup(p:Pick<BrowserPhoto,'status_label'|'detection_state'>):string {
 const label=p.status_label||'';
 if(/failed/i.test(label)||p.detection_state==='failed')return 'failed';
 if(label.startsWith('Reviewed'))return 'reviewed';
 if(label.startsWith('No bears'))return 'empty';
 if(label.startsWith('Ready')||label.startsWith('Partially'))return 'needs-review';
 return 'processing';
}
export type BrowserFilters={query:string;status:string;bear:string;sort:string;page:number};
export function browsePhotos<T extends BrowserPhoto>(photos:T[],filters:BrowserFilters){
 const query=filters.query.trim().toLocaleLowerCase();
 const filtered=photos.filter(p=>(!query||p.filename.toLocaleLowerCase().includes(query))&&(filters.status==='all'||statusGroup(p)===filters.status)&&(!filters.bear||p.bear_ids?.includes(filters.bear)));
 filtered.sort((a,b)=>{
  if(filters.sort==='name')return a.filename.localeCompare(b.filename,undefined,{numeric:true})||a.id.localeCompare(b.id);
  const delta=(Date.parse(a.created_at||'')||0)-(Date.parse(b.created_at||'')||0);
  return (filters.sort==='oldest'?delta:-delta)||a.id.localeCompare(b.id);
 });
 const pages=Math.max(1,Math.ceil(filtered.length/25));
 const page=Math.min(Math.max(0,filters.page),pages-1);
 return {items:filtered.slice(page*25,page*25+25),total:filtered.length,pages,page,ids:new Set(filtered.map(p=>p.id))};
}
