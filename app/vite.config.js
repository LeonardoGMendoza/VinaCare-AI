import { defineConfig } from 'vite'

// Mesmo alvo do PerTo Saude: o build converte o codigo para iPhones com iOS antigo.
export default defineConfig({
  base: './',
  build: {
    target: ['es2020', 'safari13', 'ios13'],
    outDir: '../demo',
    emptyOutDir: true,
    chunkSizeWarningLimit: 2000
  }
})
