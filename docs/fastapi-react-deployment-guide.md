# FastAPI + React 一体化部署完整指南

## 使用场景

我有一个 FastAPI 后端 + React 前端应用，想要配置为简单的一体化部署模式。

## 需求

1. 前端通过 `npm run build` 构建为静态文件
2. FastAPI 同时服务 API 请求和静态文件
3. 前端通过 `/api` 前缀访问后端 API
4. 支持 SPA 路由（React Router）
5. 开发环境使用 Vite proxy，生产环境统一服务

## 目标

配置 FastAPI + React 应用，实现前后端一体化部署，简化部署流程。

## 架构方案

采用**前后端一体化部署**模式：
- 前端通过构建工具（Vite/Webpack/CRA）构建为静态文件
- FastAPI 同时服务 API 请求和静态文件
- 生产环境中，所有请求通过同一个服务处理

## 典型项目结构

假设你的项目结构如下（可根据实际情况调整）：

```
your-project/
├── main.py                 # FastAPI 后端入口（文件名可自定义）
├── requirements.txt         # Python 依赖
├── Dockerfile              # Docker 构建配置
├── Procfile                # PaaS 运行命令（可选）
├── .dockerignore           # Docker 忽略文件
├── frontend/               # 前端目录（目录名可自定义）
│   ├── src/
│   ├── package.json
│   ├── vite.config.js      # Vite 配置
│   └── dist/               # 构建输出（自动生成，目录名取决于构建工具）
└── scripts/                # 脚本目录（可选）
    └── deploy_koyeb.py     # Koyeb 部署脚本（可选，仅用于 Koyeb）
```

### 适配不同项目结构

如果你的项目结构不同，需要相应调整：

1. **前端目录名不同**（例如 `client/`、`web/`、`ui/`）：
   - 修改 `main.py` 中的 `frontend_dist = Path("frontend/dist")` 为你的目录名
   - 修改 `Dockerfile` 中的 `COPY frontend/` 路径
   - 修改 `vite.config.js` 的路径（如果配置文件位置不同）

2. **前端在根目录**（不是子目录）：
   - 修改 `main.py` 中的路径为 `Path("dist")`
   - 修改 `Dockerfile`，移除 `frontend/` 前缀
   - 调整构建脚本路径

3. **后端入口文件不同**（例如 `app.py`、`server.py`）：
   - 修改 `Procfile` 中的 `main:app` 为 `your-file:app`
   - 修改 `Dockerfile` CMD 中的模块名

4. **构建输出目录不同**（例如 `build/`、`public/`）：
   - 修改 `main.py` 中的 `dist` 为你的输出目录名
   - 修改 `Dockerfile` 中的复制路径

## 需要修改/创建的文件

1. `frontend/vite.config.js` - 配置构建输出和开发代理
2. `main.py` - 添加静态文件服务和 API 路由前缀
3. `Dockerfile` - 多阶段构建，包含前端构建步骤
4. `frontend/src/**` - API 调用统一使用 `/api` 前缀
5. `Procfile` - 定义运行命令（用于 Koyeb/Heroku 等 PaaS 平台）
6. `.dockerignore` - 排除不需要的文件
7. `scripts/deploy_koyeb.py` - Koyeb 部署脚本（可选，仅用于 Koyeb）

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

**为什么需要 `base: './'`？**
- 默认情况下，Vite 构建使用绝对路径（`/assets/...`）
- 在生产环境中，如果应用部署在子路径下，绝对路径会导致资源加载失败
- 使用相对路径（`./assets/...`）可以确保资源在任何路径下都能正确加载

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
from fastapi import FastAPI, HTTPException
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

# 注册 API 路由（只使用 /api 前缀，根路径留给前端）
app.include_router(api_router, prefix="/api", tags=["api"])

# 服务前端静态文件（必须在所有 API 路由之后）
frontend_dist = Path("frontend/dist")
if frontend_dist.exists():
    # 服务静态资源（CSS, JS, images 等）
    app.mount("/static", StaticFiles(directory=str(frontend_dist / "assets")), name="static")
    
    # 服务前端根路径
    @app.get("/")
    async def serve_frontend_root():
        """Serve frontend index.html for root path."""
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Frontend not found")
    
    # 服务前端页面（SPA 路由回退）
    @app.get("/{path:path}")
    async def serve_frontend(path: str):
        """Serve frontend files, fallback to index.html for SPA routing."""
        # 跳过 API 路由和 docs
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

**为什么需要这样的路由顺序？**

1. **API 路由先注册**：确保 `/api/*` 路径优先匹配 API 端点
2. **静态文件后注册**：避免静态文件路径覆盖 API 路由
3. **根路径单独处理**：`/` 路径必须明确返回 `index.html`，不能依赖通配符
4. **SPA 路由回退**：所有未匹配的路径都返回 `index.html`，让前端路由处理

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

**为什么使用 `/api` 前缀？**

- **开发环境**：Vite proxy 可以轻松识别并转发 `/api` 请求到后端
- **生产环境**：前后端同源，无需 CORS 配置
- **路由区分**：清晰区分 API 请求和前端路由
- **避免冲突**：防止前端路由与 API 端点冲突

### 4. Dockerfile 配置

```dockerfile
# 多阶段构建：先构建前端
FROM node:18-slim AS frontend-builder

WORKDIR /app/frontend

# 复制前端 package.json（如果存在）
COPY frontend/package*.json ./

# 安装依赖（npm install 默认会安装所有依赖包括 devDependencies）
RUN if [ -f package.json ]; then \
      npm install; \
    else \
      echo "No package.json found, skipping npm install"; \
    fi

# 复制前端文件
COPY frontend/ .

# 构建前端（如果 package.json 存在）
RUN if [ -f package.json ]; then \
      npm run build; \
    else \
      echo "No package.json found, skipping build"; \
      mkdir -p dist && echo "<html><body>Frontend not built</body></html>" > dist/index.html; \
    fi

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

**为什么使用多阶段构建？**

- **减小镜像大小**：最终镜像不包含 Node.js 和 node_modules
- **构建隔离**：前端构建错误不会影响后端镜像
- **缓存优化**：Docker 可以缓存各个构建阶段
- **安全性**：生产镜像不包含构建工具

**⚠️ 重要：CMD 中必须使用 `--host 0.0.0.0`**

- 使用 `0.0.0.0` 绑定所有网络接口，允许从容器外部访问
- 不要使用 `127.0.0.1` 或 `localhost`，这些只能从容器内部访问
- 这是 Docker 部署时最常见的问题之一

### 5. Procfile 配置（用于 Koyeb 等 PaaS）

创建 `Procfile` 文件，定义运行命令：

```
web: python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}
```

**为什么需要 Procfile？**

- Koyeb、Heroku 等 PaaS 平台需要知道如何启动应用
- 如果 Dockerfile 有 CMD，通常不需要 Procfile
- 但有些平台优先使用 Procfile，所以最好两个都提供

**⚠️ 重要：必须使用 `--host 0.0.0.0`**

- 使用 `0.0.0.0` 绑定所有网络接口，允许从外部访问
- 不要使用 `127.0.0.1` 或 `localhost`，这些只能从容器内部访问
- 这是部署到容器或 PaaS 平台时最常见的问题之一

### 6. .dockerignore 配置

创建 `.dockerignore` 文件，排除不需要的文件：

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
*.md
docs/
```

**为什么需要 .dockerignore？**

- **减小构建上下文**：Docker 构建时只发送需要的文件
- **加快构建速度**：减少传输时间
- **避免覆盖**：防止本地文件覆盖容器内构建的文件
- **安全性**：避免将敏感文件（如 `.env`）打包到镜像中

### 7. 启动脚本（可选）

创建 `scripts/launch.sh` 用于本地开发：

```bash
#!/bin/bash
set -e

# 1. 安装 Python 依赖
# 根据你的虚拟环境调整（.venv、venv、或直接使用系统 Python）
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi
pip install -r requirements.txt

# 2. 构建前端
# 根据你的前端目录调整路径
cd frontend
npm install
npm run build
cd ..

# 3. 启动服务
# 根据你的入口文件调整（main:app、app:app 等）
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

**注意**：根据你的项目结构调整脚本中的路径和命令。

## Koyeb 部署配置

### 环境变量

- `PORT`: Koyeb 会自动设置，应用应使用此端口
- 其他环境变量：通过 Koyeb Secrets 配置（如 API keys、数据库连接等）

### 部署脚本（可选）

如果使用 Koyeb，可以使用 `scripts/deploy_koyeb.py` 自动部署：

```bash
python scripts/deploy_koyeb.py
```

脚本会自动：
- 创建或更新 Koyeb 应用和服务
- 配置 Git 仓库连接（格式：`github.com/<org>/<repo>`）
- 设置环境变量和 Secrets
- 使用 nano 实例类型和 na 区域（可配置）

### 部署脚本参数

```bash
python scripts/deploy_koyeb.py \
  --repo https://github.com/your-org/your-repo \
  --app-name your-app-name \
  --branch master \
  --port 8001 \
  --secret-ref YOUR_SECRET_NAME
```

**注意**：
- 脚本默认会自动引用 `OPENAI_API_KEY` Secret（如果存在）。如果需要引用其他 Secrets，使用 `--secret-ref` 参数。
- 如果不需要自动引用 `OPENAI_API_KEY`，可以修改脚本中的默认行为，或使用 `--secret-ref` 显式指定所有需要的 Secrets。
- 脚本中的默认值（如应用名、端口、实例类型等）可以根据你的项目需求修改。

### Koyeb API 配置要点

根据 [Koyeb API 文档](https://api.prod.koyeb.com/public.swagger.json)：

1. **Git 仓库格式**：必须使用 `github.com/<org>/<repo>` 格式，不是完整 URL
2. **服务定义结构**：
   - `scalings` 必须是数组：`[{"min": 1, "max": 1}]`
   - `instance_types` 必须是数组：`[{"type": "nano"}]`
   - `CreateService` 只需要 `app_id` 和 `definition`，不需要顶层 `name`
3. **运行命令**：通过 Procfile 或 Dockerfile CMD 定义

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

# 运行容器（根据你的应用需要设置环境变量）
docker run -p 8001:8001 \
  -e PORT=8001 \
  -e YOUR_API_KEY=your-key \
  your-app-name

# 访问 http://localhost:8001 验证
```

## 常见问题排查

### 问题 1: 前端页面空白

**症状**：访问根路径显示空白页面或错误

**可能原因**：
- `frontend/dist` 目录不存在或为空
- 静态文件路径配置错误
- 浏览器控制台有 JavaScript 错误

**解决方法**：
1. 检查浏览器控制台是否有错误
2. 确认 `frontend/dist` 目录存在且包含文件
3. 检查 `vite.config.js` 中的 `base: './'` 配置
4. 检查 `main.py` 中的静态文件挂载路径是否正确

### 问题 2: API 调用失败

**症状**：前端无法调用后端 API，返回 404 或 CORS 错误

**可能原因**：
- 后端服务未运行
- API 路径前缀不正确
- CORS 配置问题（生产环境不应该有）

**解决方法**：
1. 确认后端服务正在运行
2. 检查前端 API 调用是否使用 `/api` 前缀
3. 查看后端日志是否有错误
4. 验证 API 端点是否在 `/api` 路径下注册

### 问题 3: 静态资源 404

**症状**：CSS、JS 文件加载失败，返回 404

**可能原因**：
- `frontend/dist/assets` 目录不存在
- 静态文件挂载路径错误
- Vite 构建配置问题

**解决方法**：
1. 确认 `frontend/dist/assets` 目录存在
2. 检查 `main.py` 中的静态文件挂载路径是否正确
3. 验证 Vite 构建输出目录配置
4. 检查浏览器 Network 标签，查看实际请求的路径

### 问题 4: 构建失败（缺少依赖）

**症状**：`npm run build` 失败，提示缺少模块

**可能原因**：
- `package.json` 中缺少依赖
- `node_modules` 未正确安装
- 使用了未声明的包

**解决方法**：
1. 运行 `npm install` 安装所有依赖
2. 检查 `package.json` 是否包含所有使用的包（如 axios）
3. 查看构建错误信息，添加缺失的依赖
4. 删除 `node_modules` 和 `package-lock.json`，重新安装

### 问题 5: 访问根路径 `/` 显示 API 响应而不是前端页面

**症状**：访问 `http://localhost:8001/` 返回 JSON 而不是 HTML

**原因**：API 路由注册到了根路径，覆盖了前端服务

**解决方法**：
1. **检查代码**：确保只使用 `app.include_router(api_router, prefix="/api")`
2. **避免错误**：不要注册不带前缀的版本，如 `app.include_router(api_router, tags=["api"])`
3. **验证**：
   - 访问 `http://localhost:8001/` 应该显示前端页面
   - 访问 `http://localhost:8001/api/health` 应该返回 API 响应

### 问题 6: SPA 路由刷新后 404

**症状**：直接访问 `/some-route` 或刷新页面返回 404

**原因**：后端没有配置 SPA 路由回退

**解决方法**：
1. 确保 `main.py` 中有 `/{path:path}` 路由处理函数
2. 该函数应该检查文件是否存在，不存在则返回 `index.html`
3. 确保该路由在所有 API 路由之后注册

### 问题 7: Koyeb 部署失败 - "no command to run"

**症状**：Koyeb 部署时提示没有运行命令

**原因**：缺少 Procfile 或 Dockerfile CMD

**解决方法**：
1. 创建 `Procfile` 文件，包含运行命令
2. 确保 Dockerfile 有 `CMD` 指令
3. 将 Procfile 提交到 Git 仓库
4. 重新部署服务

### 问题 8: Koyeb API 错误 - "error_processing_request"

**症状**：使用部署脚本时返回通用错误

**原因**：API payload 格式不正确

**解决方法**：
1. 检查 Git 仓库格式：必须是 `github.com/<org>/<repo>`
2. 检查 `scalings` 格式：必须是数组 `[{...}]`，不是对象 `{...}`
3. 检查 `instance_types` 格式：必须是数组
4. 查看详细的错误信息（脚本会显示请求和响应）

### 问题 9: 应用无法从外部访问（容器/部署环境）

**症状**：应用在容器或部署环境中运行，但无法从外部访问，返回 "Connection refused" 或超时

**原因**：应用绑定到了 `127.0.0.1` 或 `localhost`，而不是 `0.0.0.0`

**为什么会出现这个问题？**
- `127.0.0.1` 和 `localhost` 只绑定到本地回环接口，只能从容器内部访问
- 在 Docker 容器、Koyeb、Heroku 等部署环境中，外部请求需要通过容器的网络接口
- 必须使用 `0.0.0.0` 绑定所有网络接口，才能从外部访问

**解决方法**：
1. **检查启动命令**：确保所有启动命令都使用 `--host 0.0.0.0`：
   ```bash
   # ✅ 正确
   python -m uvicorn main:app --host 0.0.0.0 --port 8001
   
   # ❌ 错误（容器/部署环境）
   python -m uvicorn main:app --host 127.0.0.1 --port 8001
   python -m uvicorn main:app --host localhost --port 8001
   ```

2. **检查 Procfile**：确保使用 `0.0.0.0`：
   ```
   web: python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}
   ```

3. **检查 Dockerfile CMD**：确保使用 `0.0.0.0`：
   ```dockerfile
   CMD sh -c "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"
   ```

4. **检查 main.py**（如果使用 `uvicorn.run`）：
   ```python
   # ✅ 正确
   uvicorn.run(app, host="0.0.0.0", port=8001)
   
   # ❌ 错误
   uvicorn.run(app, host="127.0.0.1", port=8001)
   ```

5. **本地开发环境**：本地开发时可以使用 `127.0.0.1` 或 `localhost`，但建议统一使用 `0.0.0.0` 以避免部署时的混淆

**验证方法**：
- 在容器内运行：`curl http://0.0.0.0:8001/api/health` 应该成功
- 从外部访问：`curl http://<container-ip>:8001/api/health` 应该成功
- 如果绑定到 `127.0.0.1`，外部访问会失败

## 关键要点

### 1. API 路由前缀

统一使用 `/api` 前缀，便于前端代理和路由区分

- ⚠️ **重要**：只注册带 `/api` 前缀的 API 路由，不要注册到根路径
- **使用**：`app.include_router(api_router, prefix="/api")`
- **避免**：`app.include_router(api_router)`（这会覆盖根路径的前端服务）

### 2. 静态文件服务顺序

必须在所有 API 路由之后注册静态文件服务

- 先注册 API 路由，再注册静态文件服务
- 确保根路径 `/` 的处理函数在最后定义

### 3. 根路径处理

必须为根路径 `/` 单独定义处理函数

- 不要依赖 `/{path:path}` 来处理根路径
- 根路径应该直接返回 `index.html`

### 4. SPA 路由回退

所有未匹配的路由都返回 `index.html`，让前端路由处理

- `/{path:path}` 函数处理所有非 API 路径
- 如果文件不存在，回退到 `index.html`

### 5. 构建输出目录

确保前端构建输出到 `frontend/dist`（或相应目录）

**注意**：如果你的前端构建输出目录不同（例如 `frontend/build` 或 `dist`），需要相应修改 `main.py` 中的路径配置。

### 6. 开发环境代理

使用 Vite/Webpack 的 proxy 功能，开发时无需 CORS

### 7. 生产环境端口

使用环境变量 `PORT`，Koyeb、Heroku 等平台会自动设置

**注意**：默认端口可以根据你的应用调整。如果使用不同的端口，需要修改：
- `Procfile` 中的端口号
- `Dockerfile` 中的 `ENV PORT` 和 `CMD` 中的端口
- `vite.config.js` 中的 proxy target 端口（开发环境）

### 8. 主机绑定地址（重要！）

**必须使用 `0.0.0.0` 而不是 `127.0.0.1` 或 `localhost`**

这是部署到容器或 PaaS 平台时最常见的问题之一。

**为什么必须使用 `0.0.0.0`？**
- `0.0.0.0` 绑定到所有网络接口，允许从外部访问
- `127.0.0.1` 和 `localhost` 只绑定到本地回环接口，只能从容器内部访问
- 在 Docker、Koyeb、Heroku 等环境中，外部请求必须通过容器的网络接口

**所有启动命令都必须使用 `0.0.0.0`：**
- ✅ `uvicorn main:app --host 0.0.0.0 --port 8001`
- ❌ `uvicorn main:app --host 127.0.0.1 --port 8001`
- ❌ `uvicorn main:app --host localhost --port 8001`

**需要检查的地方：**
1. `Procfile` 中的启动命令
2. `Dockerfile` 中的 `CMD` 指令
3. `scripts/launch.sh` 中的启动命令
4. `main.py` 中的 `uvicorn.run()` 调用（如果使用）

**本地开发环境**：虽然本地开发可以使用 `127.0.0.1`，但建议统一使用 `0.0.0.0` 以避免部署时的混淆。

## 验证清单

部署前请确认：

- [ ] 前端依赖已安装（`npm install`）
- [ ] 前端构建成功，生成 `frontend/dist` 目录
- [ ] 本地测试通过（使用 `./scripts/launch.sh`）
- [ ] 后端可以访问 `/api/health` 等 API 端点
- [ ] 访问根路径 `/` 显示前端页面
- [ ] 前端 API 调用使用 `/api` 前缀
- [ ] SPA 路由（如 `/about`）正常工作
- [ ] Docker 构建成功，镜像包含前端静态文件
- [ ] Docker 容器运行正常，功能完整
- [ ] Procfile 已创建并提交到 Git
- [ ] **所有启动命令都使用 `--host 0.0.0.0`（不是 `127.0.0.1` 或 `localhost`）**
- [ ] Koyeb 部署脚本配置正确（如使用 Koyeb）
- [ ] 所有路径配置与你的项目结构匹配

## 期望结果

配置完成后，应该实现：

- ✅ 运行 `npm run build` 后，前端构建到 `frontend/dist`
- ✅ FastAPI 自动服务 `frontend/dist` 中的静态文件
- ✅ 访问 `/` 显示前端页面，访问 `/api/*` 调用后端 API
- ✅ Docker 构建时自动构建前端并包含在镜像中
- ✅ Koyeb 部署时自动检测并运行应用
- ✅ 开发环境使用 Vite proxy，无需 CORS
- ✅ 生产环境前后端同源，性能足够

## 优势

- ✅ **部署简单**：只需一个服务，一个端口
- ✅ **无需 CORS 配置**：前后端同源
- ✅ **适合中小型应用**：性能足够
- ✅ **开发友好**：开发环境使用代理，生产环境统一服务
- ✅ **成本低**：单个服务，资源占用少

## 自定义和扩展

### 修改默认配置

文档中的所有配置都可以根据你的项目需求调整：

1. **端口号**：默认 8001，可以在 `Procfile`、`Dockerfile`、`vite.config.js` 中修改
2. **API 前缀**：默认 `/api`，可以在 `main.py` 和 `vite.config.js` 中修改
3. **前端目录**：默认 `frontend/`，需要修改所有相关路径
4. **构建输出**：默认 `dist/`，需要修改 `main.py` 和 `Dockerfile`
5. **实例类型和区域**：Koyeb 部署脚本默认使用 `nano` 和 `na`，可以通过修改脚本调整

### 适配其他 PaaS 平台

虽然文档以 Koyeb 为例，但配置同样适用于其他平台：

- **Heroku**：使用 `Procfile`，配置类似
- **Railway**：支持 Dockerfile，配置相同
- **Fly.io**：支持 Dockerfile，可能需要额外的配置文件
- **Render**：支持 Dockerfile 和 Procfile
- **其他平台**：大多数现代 PaaS 都支持 Dockerfile

## 注意事项

- **性能**：静态文件由 FastAPI 服务，不是最优性能方案（但对于中小型应用足够）
- **扩展性**：如需更高性能，可考虑使用 Nginx 反向代理
- **路径配置**：确保前端构建时使用相对路径（`base: './'`），避免路径问题
- **环境变量**：生产环境使用环境变量管理配置，不要硬编码
- **项目特定配置**：文档中的示例需要根据你的实际项目结构调整

## 相关资源

- [FastAPI 静态文件服务文档](https://fastapi.tiangolo.com/tutorial/static-files/)
- [Vite 配置文档](https://vitejs.dev/config/)
- [Koyeb API 文档](https://api.prod.koyeb.com/public.swagger.json)
- [Koyeb 部署指南](https://www.koyeb.com/docs)
