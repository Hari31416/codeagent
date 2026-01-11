import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

export default defineConfig(({ mode }) => {
  // Load env file from the current directory (frontend/)
  const env = loadEnv(mode, __dirname, '')
  const basePath = env.VITE_BASE_PATH || '/'

  return {
    base: basePath,
    plugins: [react(), tailwindcss()],
    envDir: './',
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: parseInt(env.VITE_PORT || '5170'),
      strictPort: true,
      allowedHosts: env.VITE_ALLOWED_HOSTS ? env.VITE_ALLOWED_HOSTS.split(',') : true,
      hmr: {
        protocol: env.VITE_HMR_PROTOCOL || 'wss',
        host: env.VITE_HMR_HOST || 'apps.hari31416.in',
        clientPort: parseInt(env.VITE_HMR_PORT || '443'),
        path: 'ws-hmr',
      },
      watch: {
        usePolling: true,
      },
    },
    preview: {
      host: '0.0.0.0',
      port: parseInt(env.VITE_PORT || '5573'),
      strictPort: true,
    },
  }
})
