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

## 期望结果
- 运行 `npm run build` 后，前端构建到 `frontend/dist`
- FastAPI 自动服务 `frontend/dist` 中的静态文件
- 访问 `/` 显示前端页面，访问 `/api/*` 调用后端 API
- Docker 构建时自动构建前端并包含在镜像中

## 请提供
1. 修改后的 `vite.config.js` 配置
2. 修改后的 `main.py` 代码（包含静态文件服务逻辑）
3. 前端 API 调用的最佳实践示例
4. Dockerfile 多阶段构建配置
5. 本地开发启动脚本（可选）

