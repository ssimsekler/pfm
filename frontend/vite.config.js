import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Production is served as a static build via nginx + Traefik (see Dockerfile).
// For the Docker dev workflow (infra/docker-compose.override.yml) the dev server
// runs inside the `frontend` container on port 80 behind Traefik, so it must
// bind 0.0.0.0, allow the proxied host, and use the browser origin for HMR.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // listen on 0.0.0.0 (needed inside the container)
    port: 80, // matches Traefik's frontend service (http://frontend:80)
    allowedHosts: true, // accept the Host header forwarded by Traefik (localhost)
    hmr: { clientPort: 80 }, // HMR websocket goes back through Traefik on :80
    // Local (non-Docker) dev can still proxy the API to a local backend.
    proxy: { "/api": "http://localhost:8000" },
  },
  build: {
    outDir: "dist",
  },
});
