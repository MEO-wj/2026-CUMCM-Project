import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  // Reuse the original Three.js material assets without copying or modifying them.
  publicDir: '../原理图/public',
  resolve: { alias: [
    { find: /^three$/, replacement: fileURLToPath(new URL('./node_modules/three/build/three.module.js', import.meta.url)) },
    { find: /^three\/addons\//, replacement: fileURLToPath(new URL('./node_modules/three/examples/jsm/', import.meta.url)) },
  ] },
  server: { fs: { allow: ['..'] } },
});
