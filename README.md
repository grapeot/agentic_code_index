# Code Indexing Agent

一个基于 LLM Agent 的智能代码索引与查询系统，支持通过自然语言与代码库进行深度对话。

## 演示视频

[查看演示视频](docs/screenshot.mp4)

## 功能特性

- ✅ **双层索引结构**: 文件索引和函数索引分离，支持从宏观到微观的多层次代码探索
- ✅ **语义搜索**: 基于 FAISS 向量索引的语义搜索，支持文件和函数级别的精确查询
- ✅ **LLM 驱动的代码解析**: 使用 LLM 识别函数边界，灵活处理各种代码结构
- ✅ **Agent 多轮工具调用**: 智能 Agent 通过多轮迭代探索代码库，自主调整查询策略
- ✅ **结构化输出**: 利用 OpenAI 结构化输出功能，保证 Agent 输出的可靠性和类型安全
- ✅ **FastAPI 服务接口**: 提供完整的 RESTful API，支持索引和查询操作
- ✅ **React 前端界面**: 提供直观的 Web 界面，支持代码浏览和交互式查询

## 关键设计决策

本项目的核心设计遵循以下关键决策（详细设计文档请参考 [设计文档](docs/design.md)）：

- **双层索引结构**: 采用文件索引和函数索引的分离式设计，赋予查询 Agent 控制信息粒度的能力，支持从宏观到微观的多层次代码探索
- **LLM 驱动的代码结构解析**: 使用 LLM 识别函数边界，提供比传统解析器更强的灵活性，可处理语法不完整或非标准的代码片段
- **FAISS IndexFlatL2 向量搜索**: 选择精确的 L2 距离计算索引，保证 100% 召回率，适合中小型代码库，未来可平滑过渡到近似最近邻索引
- **OpenAI text-embedding-3-small**: 在性能和成本之间取得平衡的主流 embedding 模型选择
- **FastAPI + Pydantic 结构化输出**: 利用 OpenAI 的结构化输出功能，通过 Pydantic Schema 强制保证 Agent 输出的可靠性和类型安全

更多设计细节、架构图和实现原理，请参阅 [设计文档](docs/design.md)。

## 安装

```bash
# 创建虚拟环境（如果还没有）
uv venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt
```

## 环境变量

确保设置了 OpenAI API Key：

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## 运行服务

### 一键启动（推荐）

使用启动脚本一键启动完整应用（包含前端构建和后端服务）：

```bash
./scripts/launch.sh
```

这个脚本会自动：
1. 创建并激活 Python 虚拟环境（如果不存在）
2. 安装 Python 依赖
3. 安装前端依赖（如果不存在）
4. 构建前端静态文件
5. 启动 FastAPI 服务器

启动后访问：
- **前端界面**: http://localhost:8001/
- **API 文档**: http://localhost:8001/docs
- **健康检查**: http://localhost:8001/api/health

### 手动启动（开发模式）

如果需要分别启动前后端进行开发：

#### 后端服务

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动 FastAPI 服务（使用 8001 端口）
python -m uvicorn main:app --port 8001 --reload
```

#### 前端开发服务器

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器将在 `http://localhost:3000` 启动（通过 Vite 代理连接到后端 API）。

### 生产部署

在生产环境中，前端会被构建为静态文件，由 FastAPI 统一服务。部署到 Koyeb 时，Dockerfile 会自动处理前端构建。

**部署到 Koyeb**:
```bash
python deploy_koyeb.py --force-api
```

**注意**: 确保在 Koyeb 控制台中已创建 `OPENAI_API_KEY` Secret，部署脚本会自动引用它。

## API 使用

### 1. 索引代码库

首先需要为代码库创建索引：

```bash
curl -X POST http://localhost:8001/index \
  -H "Content-Type: application/json" \
  -d '{
    "codebase_path": ".",
    "output_dir": "self_index"
  }'
```

**响应示例**:
```json
{
  "status": "success",
  "total_files": 25,
  "total_chunks": 156,
  "file_chunks": 25,
  "function_chunks": 131,
  "output_dir": "self_index"
}
```

### 2. 查询代码库

使用自然语言查询代码库：

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "项目中处理用户认证的逻辑在哪里？",
    "model": "gpt-5-mini",
    "max_iterations": 6
  }'
```

**响应示例**:
```json
{
  "answer": "根据代码库的搜索结果，用户认证逻辑主要位于以下位置：\n\n1. `src/auth/service.py` - 包含 `authenticate_user` 函数，负责验证用户凭据...",
  "confidence": "high",
  "sources": [
    "src/auth/service.py",
    "src/auth/middleware.py"
  ],
  "reasoning": "通过语义搜索在函数索引中找到了相关的认证函数，然后查看了完整的文件内容以确认实现细节"
}
```

### 3. 其他端点

- `GET /api/` - 获取服务信息和可用端点
- `GET /api/health` - 健康检查
- `GET /api/files` - 列出所有已索引的文件
- `GET /api/file?file_path=xxx` - 获取指定文件的内容
- `GET /api/file-tree` - 获取文件系统目录结构

**注意**: API 端点支持两种访问方式：
- 带 `/api` 前缀：`/api/query`（推荐，前端使用）
- 直接访问：`/query`（向后兼容）

## 使用示例

### 示例 1: 查找特定功能的实现

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "如何实现代码索引功能？",
    "model": "gpt-5-mini",
    "max_iterations": 6
  }'
```

### 示例 2: 查找特定函数

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "search_codebase 函数的具体实现是什么？",
    "model": "gpt-5-mini",
    "max_iterations": 6
  }'
```

### 示例 3: 了解项目结构

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "这个项目的主要模块有哪些？",
    "model": "gpt-5-mini",
    "max_iterations": 6
  }'
```

## 测试

运行测试套件：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 运行基础测试
python tests/test_mvp.py

# 运行索引测试
python tests/test_index.py

# 运行查询测试
python tests/test_query.py

# 运行综合测试
python tests/test_comprehensive.py
```

## 项目结构

```
.
├── main.py              # FastAPI 服务入口
├── src/                 # 源代码目录
│   ├── agent.py         # Agent 核心逻辑
│   ├── indexing.py      # 代码索引服务
│   ├── search.py        # 代码搜索服务
│   ├── tools.py         # Agent 工具函数（语义搜索、文件查看等）
│   └── models.py        # Pydantic 数据模型
├── frontend/            # React 前端应用
│   ├── src/             # 前端源代码
│   │   ├── App.jsx      # 主应用组件
│   │   └── components/  # UI 组件
│   │       ├── ChatPanel.jsx    # 聊天面板
│   │       ├── CodeViewer.jsx   # 代码查看器
│   │       └── FileTree.jsx     # 文件树
│   └── ...
├── tests/               # 测试脚本目录
│   ├── test_mvp.py      # MVP 测试脚本
│   ├── test_index.py    # 索引测试脚本
│   ├── test_query.py    # 查询测试脚本
│   └── test_comprehensive.py  # 综合测试
├── self_index/          # 示例索引数据
│   ├── file_index.faiss      # 文件级别向量索引
│   ├── function_index.faiss  # 函数级别向量索引
│   └── metadata.json          # 索引元数据
├── docs/                # 文档
│   ├── design.md        # 设计文档
│   └── screenshot.mp4   # 演示视频
├── requirements.txt     # Python 依赖列表
├── Dockerfile           # Docker 构建文件（用于生产部署）
├── deploy_koyeb.py      # Koyeb 部署脚本
├── scripts/             # 脚本目录
│   ├── launch.sh        # 一键启动脚本（推荐）
│   └── update_self_index.py  # 更新自索引脚本
└── README.md            # 本文件
```

## 核心流程

### 索引流程

1. **遍历文件**: 递归遍历代码库中的所有支持的源文件（.py, .js, .ts, .go 等）
2. **结构解析**: 使用 LLM 识别每个文件中的函数边界（函数名、起始行、结束行）
3. **数据分块**: 创建文件级别和函数级别的代码块
4. **向量化**: 使用 OpenAI text-embedding-3-small 生成 embedding 向量
5. **构建索引**: 使用 FAISS IndexFlatL2 构建向量索引并保存

### 查询流程

1. **接收查询**: Agent 接收用户的自然语言问题
2. **多轮迭代**: Agent 可以调用工具（语义搜索、文件查看）最多 N 轮
   - **语义搜索**: 在文件索引或函数索引中搜索相关代码
   - **文件查看**: 查看完整文件内容以获取更多上下文
3. **工具执行**: 系统执行工具并返回结果给 Agent
4. **强制总结**: 最后一轮不再提供工具，Agent 必须给出最终答案
5. **结构化输出**: 最终答案必须符合 Pydantic FinalAnswer 模型，包含答案、置信度、来源和推理过程

## 技术栈

- **后端**: Python, FastAPI, OpenAI API, FAISS, Pydantic
- **前端**: React, Vite
- **AI 模型**: OpenAI GPT-5-mini (推理), text-embedding-3-small (向量化)
- **部署**: Docker, Koyeb

## 架构说明

### 前后端集成

本项目采用**前后端一体化部署**方案：
- 前端通过 Vite 构建为静态文件（`frontend/dist`）
- FastAPI 同时服务 API 请求和静态文件
- 生产环境中，所有请求通过同一个服务处理（端口 8001）

**优势**:
- 部署简单，只需一个服务
- 无需配置 CORS
- 适合中小型应用

**API 路由**:
- 前端通过 `/api/*` 访问后端 API
- 静态文件通过根路径 `/` 访问
- FastAPI 自动处理 SPA 路由回退

## 许可证

MIT License
