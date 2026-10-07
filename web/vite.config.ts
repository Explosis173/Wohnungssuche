import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Relative base so the app works under https://<user>.github.io/<repo>/
export default defineConfig({
  base: './',
  plugins: [vue()],
})
