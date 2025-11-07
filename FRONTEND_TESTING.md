# 前端测试指南

## 前置条件

1. **后端服务已启动**
   - 确保后端服务运行在 `http://localhost:8001`
   - 如果还没启动，运行：`./launch_backend.sh`
   - 或者：`source .venv/bin/activate && uvicorn main:app --reload --port 8001`

2. **索引已加载**
   - 确保 `self_index/` 目录存在且包含完整的索引文件
   - 服务启动时会自动加载索引，看到 `✅ Loaded index from self_index` 表示成功

## 启动前端

### 1. 进入前端目录

```bash
cd frontend
```

### 2. 安装依赖（首次运行）

```bash
npm install
```

### 3. 启动开发服务器

```bash
npm run dev
```

启动成功后，你会看到类似输出：
```
  VITE v5.x.x  ready in xxx ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

### 4. 打开浏览器

在浏览器中访问：**http://localhost:3000**

## 测试功能

### 1. 文件树（左侧）
- 应该能看到代码库的文件结构
- 点击文件应该能在代码查看器中显示内容

### 2. 代码查看器（中间）
- 应该支持语法高亮
- 点击文件树中的文件应该能正确显示代码

### 3. 聊天面板（右侧）
- 输入问题，例如：
  - "这个项目有哪些主要模块？"
  - "Agent 是如何工作的？"
  - "列出所有的工具函数"
- 点击发送或按 Enter
- 应该能看到 Agent 的回答，包含：
  - 答案内容（中文正常显示）
  - 置信度
  - 来源文件列表
  - 推理过程（如果有）

### 4. 代码引用
- 如果答案中包含文件引用，应该可以点击
- 点击后应该自动跳转到对应文件并高亮相关行

## 常见问题

### 前端无法连接后端
- 检查后端是否运行在 `http://localhost:8001`
- 检查浏览器控制台是否有错误信息
- 确认 Vite 代理配置正确（`frontend/vite.config.js`）

### 中文显示乱码
- 确保后端 JSON 序列化使用了 `ensure_ascii=False`（已配置）
- 检查浏览器编码设置

### 索引未加载
- 检查后端启动日志，确认看到 `✅ Loaded index from self_index`
- 如果没有，检查 `self_index/` 目录是否存在且包含 `metadata.json`

## 开发模式

前端使用 Vite 开发服务器，支持：
- **热重载**：修改代码后自动刷新
- **代理转发**：`/api/*` 请求自动转发到后端 `http://localhost:8001/*`

## 构建生产版本

```bash
cd frontend
npm run build
```

构建产物在 `frontend/dist/` 目录。

