import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    // Host port is 5174 (docker-compose.yml maps 5174:5173 - container
    // still listens on 5173 internally, only the host-facing port moved
    // to avoid a clash with another project on this machine). Vite
    // injects `server.hmr.port` (falling back to `server.port`) into the
    // HMR client script rather than reading it from the page's actual
    // location, so without this the browser would try to open its HMR
    // websocket on host port 5173 - which nothing listens on anymore -
    // instead of the 5174 it actually loaded the page from.
    hmr: {
      clientPort: 5174,
    },
    // Docker Desktop's bind mount on Windows doesn't propagate native
    // filesystem change events reliably to chokidar inside the container,
    // so HMR silently serves stale modules without this.
    watch: {
      usePolling: true,
      interval: 300,
    },
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})
