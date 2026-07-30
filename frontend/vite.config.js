import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Phase 0 scaffold. Proxy for local dev; production is served via nginx + Traefik.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});