import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "node:path";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: process.env.BACKEND_URL ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  cacheDir: "/tmp/hrms-vite-cache",
});
