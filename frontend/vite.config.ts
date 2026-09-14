import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const apiTarget=process.env.ONLY_BEARS_API_TARGET||'http://127.0.0.1:8000';
export default defineConfig({plugins:[react()],server:{proxy:{'/api':apiTarget,'/auth':apiTarget,'/health':apiTarget}}});
