import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on IPv4 loopback so http://127.0.0.1:5173 works (Flask redirects here; default
    // "localhost" can bind only to ::1 on some Windows setups -> ERR_CONNECTION_REFUSED).
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      // Flask Telangana admin API (same paths as App.jsx expects)
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});