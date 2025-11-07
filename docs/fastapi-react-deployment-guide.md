# FastAPI + React 一体化部署配置指南

## 目标
配置 FastAPI + React 应用，实现前后端一体化部署，简化部署流程。

## 架构方案
采用**前后端一体化部署**模式：
- 前端通过构建工具（Vite/Webpack/CRA）构建为静态文件
- FastAPI 同时服务 API 请求和静态文件
- 生产环境中，所有请求通过同一个服务处理

## 实施步骤

### 1. 前端配置

#### Vite 项目配置 (`vite.config.js`)
```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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
    // 生产环境使用相对路径，便于后端服务
    base: './'
  }
})
```

#### Create React App 配置
如果使用 CRA，需要修改 `package.json`：
```json
{
  "homepage": "./"
}
```

### 2. 后端配置

#### FastAPI 主文件 (`main.py`)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

# 创建 API 路由组（用于前端 /api 前缀）
from fastapi import APIRouter
api_router = APIRouter()

# 定义你的 API 路由（使用 api_router 而不是 app）
@api_router.get("/health")
async def health():
    return {"status": "healthy"}

@api_router.post("/your-endpoint")
async def your_endpoint():
    # 你的 API 逻辑
    pass

# 注册 API 路由（支持 /api 前缀和直接访问）
app.include_router(api_router, prefix="/api", tags=["api"])
app.include_router(api_router, tags=["api"])  # 向后兼容

# 服务前端静态文件（必须在所有 API 路由之后）
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    # 服务静态资源（CSS, JS, images 等）
    app.mount("/static", StaticFiles(directory=str(frontend_dist / "assets")), name="static")
    
    # 服务前端页面（SPA 路由回退）
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Serve frontend files, fallback to index.html for SPA routing."""
        # 跳过 API 路由
        if path.startswith(("api/", "docs", "openapi.json")):
            raise HTTPException(status_code=404)
        
        file_path = frontend_dist / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # SPA 路由回退到 index.html
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        
        raise HTTPException(status_code=404)
```

### 3. 前端代码修改

#### API 调用统一使用 `/api` 前缀

```javascript
// 开发环境：Vite proxy 会转发到后端
// 生产环境：直接调用同域名的 /api 端点
const response = await fetch('/api/your-endpoint', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(data)
});
```

### 4. Dockerfile 配置

```dockerfile
# 多阶段构建：先构建前端
FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend

# 复制前端 package.json
COPY frontend/package*.json ./

# 安装依赖
RUN npm install

# 复制前端文件并构建
COPY frontend/ .
RUN npm run build

# Python 后端阶段
FROM python:3.11-slim

WORKDIR /app

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 从前端构建阶段复制构建好的静态文件
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

ENV PORT=8001

CMD sh -c "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"
```

### 5. 启动脚本（可选）

创建 `scripts/launch.sh` 用于本地开发：

```bash
#!/bin/bash
set -e

# 1. 安装 Python 依赖
source .venv/bin/activate
pip install -r requirements.txt

# 2. 构建前端
cd frontend
npm install
npm run build
cd ..

# 3. 启动服务
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

## 本地测试步骤

在部署到生产环境之前，强烈建议先在本地测试完整流程：

### 步骤 1: 确保所有依赖已安装

```bash
# 后端依赖
source .venv/bin/activate
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
cd ..
```

### 步骤 2: 构建前端

```bash
cd frontend
npm run build
cd ..
```

**检查点**：确认 `frontend/dist` 目录已生成，包含：
- `index.html`
- `assets/` 目录（包含 CSS 和 JS 文件）

### 步骤 3: 启动服务并测试

使用启动脚本（推荐）：
```bash
./scripts/launch.sh
```

或手动启动：
```bash
source .venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 步骤 4: 验证功能

在浏览器中访问 `http://localhost:8001`，检查：

1. **前端页面加载**
   - [ ] 根路径 `/` 显示前端界面
   - [ ] CSS 样式正确加载
   - [ ] JavaScript 功能正常

2. **API 端点**
   - [ ] `http://localhost:8001/api/health` 返回 `{"status": "healthy"}`
   - [ ] `http://localhost:8001/docs` 显示 API 文档

3. **前端 API 调用**
   - [ ] 前端可以成功调用 `/api/*` 端点
   - [ ] 没有 CORS 错误
   - [ ] API 响应正确显示

4. **SPA 路由**（如果使用 React Router）
   - [ ] 直接访问 `/some-route` 能正确显示页面
   - [ ] 刷新页面不会返回 404

### 步骤 5: 测试 Docker 构建（可选）

```bash
# 构建镜像
docker build -t your-app-name .

# 运行容器
docker run -p 8001:8001 -e OPENAI_API_KEY=your-key your-app-name

# 访问 http://localhost:8001 验证
```

### 常见问题排查

**问题 1: 前端页面空白**
- 检查浏览器控制台是否有错误
- 确认 `frontend/dist` 目录存在且包含文件
- 检查 `vite.config.js` 中的 `base: './'` 配置

**问题 2: API 调用失败**
- 确认后端服务正在运行
- 检查前端 API 调用是否使用 `/api` 前缀
- 查看后端日志是否有错误

**问题 3: 静态资源 404**
- 确认 `frontend/dist/assets` 目录存在
- 检查 `main.py` 中的静态文件挂载路径是否正确

**问题 4: 构建失败（缺少依赖）**
- 运行 `npm install` 安装所有依赖
- 检查 `package.json` 是否包含所有使用的包（如 axios）
- 查看构建错误信息，添加缺失的依赖

## 验证清单

- [ ] 前端依赖已安装（`npm install`）
- [ ] 前端构建成功，生成 `frontend/dist` 目录
- [ ] 本地测试通过（使用 `./scripts/launch.sh`）
- [ ] 后端可以访问 `/api/health` 等 API 端点
- [ ] 访问根路径 `/` 显示前端页面
- [ ] 前端 API 调用使用 `/api` 前缀
- [ ] SPA 路由（如 `/about`）正常工作
- [ ] Docker 构建成功，镜像包含前端静态文件
- [ ] Docker 容器运行正常，功能完整

### 6. .dockerignore 配置

```
node_modules/
frontend/node_modules/
frontend/dist/
frontend/build/
.venv/
venv/
__pycache__/
*.pyc
.git/
.env
```

## 关键要点

1. **API 路由前缀**：统一使用 `/api` 前缀，便于前端代理和路由区分
2. **静态文件服务顺序**：必须在所有 API 路由之后注册静态文件服务
3. **SPA 路由回退**：所有未匹配的路由都返回 `index.html`，让前端路由处理
4. **构建输出目录**：确保前端构建输出到 `frontend/dist`（或相应目录）
5. **开发环境代理**：使用 Vite/Webpack 的 proxy 功能，开发时无需 CORS

## 验证清单

- [ ] 前端构建成功，生成 `frontend/dist` 目录
- [ ] 后端可以访问 `/api/health` 等 API 端点
- [ ] 访问根路径 `/` 显示前端页面
- [ ] 前端 API 调用使用 `/api` 前缀
- [ ] SPA 路由（如 `/about`）正常工作
- [ ] Docker 构建成功，镜像包含前端静态文件

## 优势

- ✅ 部署简单：只需一个服务，一个端口
- ✅ 无需 CORS 配置：前后端同源
- ✅ 适合中小型应用：性能足够
- ✅ 开发友好：开发环境使用代理，生产环境统一服务

## 注意事项

- 静态文件由 FastAPI 服务，不是最优性能方案（但对于中小型应用足够）
- 如需更高性能，可考虑使用 Nginx 反向代理（见 Dockerfile.nginx 示例）
- 确保前端构建时使用相对路径（`base: './'`），避免路径问题

