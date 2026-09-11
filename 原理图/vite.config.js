import { defineConfig } from 'vite';

export default defineConfig({
  // Keep the user's current drawing stable while materials are being edited.
  server: { hmr: false },
});
