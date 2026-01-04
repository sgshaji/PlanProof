import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const isDocker = env.DOCKER_ENV === 'true' || process.env.DOCKER_ENV === 'true';
  const backendTarget = isDocker ? 'http://backend:8000' : 'http://localhost:8000';
  
  console.log(`[Vite] Proxy target: ${backendTarget} (DOCKER_ENV=${isDocker})`);
  
  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
