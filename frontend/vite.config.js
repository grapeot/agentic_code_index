import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

// 读取 .env 文件（从项目根目录）
function loadEnvFromRoot() {
  try {
    const envPath = resolve(__dirname, '../.env')
    const envContent = readFileSync(envPath, 'utf-8')
    const env = {}
    for (const line of envContent.split('\n')) {
      const trimmed = line.trim()
      if (trimmed && !trimmed.startsWith('#')) {
        const [key, ...valueParts] = trimmed.split('=')
        if (key && valueParts.length > 0) {
          env[key.trim()] = valueParts.join('=').trim().replace(/^["']|["']$/g, '')
        }
      }
    }
    return env
  } catch (error) {
    // .env 文件不存在或无法读取，返回空对象
    return {}
  }
}

// 从 .env 文件中的 SERVICE_NAME 计算基础路径
const rootEnv = loadEnvFromRoot()
const serviceName = rootEnv.SERVICE_NAME || ''
const basePath = serviceName ? `/${serviceName}` : ''

// 调试输出
if (process.env.NODE_ENV !== 'production' || basePath) {
  console.log(`[Vite Config] SERVICE_NAME from .env: ${serviceName || 'not set'}`)
  console.log(`[Vite Config] Final basePath: "${basePath}"`)
  console.log(`[Vite Config] Final base config: "${basePath ? `${basePath}/` : './'}"`)
}

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
    // 从 .env 文件中的 SERVICE_NAME 计算基础路径
    base: basePath ? `${basePath}/` : './'
  }
})

