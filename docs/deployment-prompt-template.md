# FastAPI + React 一体化部署 Prompt 模板

## 使用场景
我有一个 FastAPI 后端 + React 前端应用，想要配置为简单的一体化部署模式。

## 需求
1. 前端通过 `npm run build` 构建为静态文件
2. FastAPI 同时服务 API 请求和静态文件
3. 前端通过 `/api` 前缀访问后端 API
4. 支持 SPA 路由（React Router）
5. 开发环境使用 Vite proxy，生产环境统一服务

## 当前项目结构
- 后端：FastAPI（`main.py`）
- 前端：React + Vite（`frontend/` 目录）
- 构建工具：Vite
- 部署目标：Docker + Koyeb（或其他 PaaS）

## 需要修改的文件
1. `frontend/vite.config.js` - 配置构建输出和开发代理
2. `main.py` - 添加静态文件服务和 API 路由前缀
3. `Dockerfile` - 多阶段构建，包含前端构建步骤
4. `frontend/src/**` - API 调用统一使用 `/api` 前缀
5. `Procfile` - 定义运行命令（用于 Koyeb 等 PaaS 平台）
6. `scripts/deploy_koyeb.py` - Koyeb 部署脚本（可选）

## 期望结果
- 运行 `npm run build` 后，前端构建到 `frontend/dist`
- FastAPI 自动服务 `frontend/dist` 中的静态文件
- 访问 `/` 显示前端页面，访问 `/api/*` 调用后端 API
- Docker 构建时自动构建前端并包含在镜像中
- Koyeb 部署时自动检测并运行应用

## Koyeb 部署配置

### Procfile
创建 `Procfile` 文件，定义运行命令：
```
web: python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}
```

### Dockerfile CMD
确保 Dockerfile 包含运行命令：
```dockerfile
CMD sh -c "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"
```

### 环境变量
- `PORT`: Koyeb 会自动设置，应用应使用此端口
- `OPENAI_API_KEY`: 通过 Koyeb Secrets 配置

### 部署脚本
使用 `scripts/deploy_koyeb.py` 自动部署：
```bash
python scripts/deploy_koyeb.py
```

脚本会自动：
- 创建或更新 Koyeb 应用和服务
- 配置 Git 仓库连接
- 设置环境变量和 Secrets
- 使用 nano 实例类型和 na 区域（可配置）

## 请提供
1. 修改后的 `vite.config.js` 配置
2. 修改后的 `main.py` 代码（包含静态文件服务逻辑）
3. 前端 API 调用的最佳实践示例
4. Dockerfile 多阶段构建配置
5. `Procfile` 配置
6. Koyeb 部署脚本（可选）
7. 本地开发启动脚本（可选）

