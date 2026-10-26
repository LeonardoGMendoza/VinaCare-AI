import { defineConfig } from 'vite'
import { resolve } from 'node:path'

// Mesmo alvo do PerTo Saude: o build converte o codigo para iPhones com iOS antigo.
export default defineConfig({
  base: './',
  build: {
    target: ['es2020', 'safari13', 'ios13'],
    outDir: '../demo',
    emptyOutDir: true,
    chunkSizeWarningLimit: 2000,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'),
        coleta: resolve(__dirname, 'coleta.html'),
        exercicio: resolve(__dirname, 'exercicio.html')
      }
    }
  }
})
