import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 获取基础路径：支持子路径部署
// 通过环境变量 VITE_BASE_PATH 设置（Vite 要求以 VITE_ 开头）
// 或者通过构建时的环境变量 BASE_PATH（在 Dockerfile 中设置）
const basePath = process.env.VITE_BASE_PATH || process.env.BASE_PATH || ''

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  },
  build: {
    outDir: 'dist',
    // 支持子路径部署：通过环境变量设置基础路径
    // 如果未设置，使用相对路径 './'（适用于根路径部署）
    // 如果设置了，例如 BASE_PATH=/test-service，则使用 '/test-service/'
    base: basePath ? `${basePath}/` : './'
  }
})

