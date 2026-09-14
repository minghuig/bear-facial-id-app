import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig(({mode})=>{
 const local=mode==='local-cpu';
 const apiTarget=process.env.ONLY_BEARS_API_TARGET||(local?'http://127.0.0.1:18000':'http://127.0.0.1:8000');
 return {plugins:[react()],server:{port:local?5174:undefined,strictPort:local,proxy:{'/api':apiTarget,'/auth':apiTarget,'/health':apiTarget}}};
});
