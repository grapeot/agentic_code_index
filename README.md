# Code Indexing Agent MVP

这是一个用于验证 Agentic 代码索引系统技术可行性的最小可行产品（MVP）。

## 功能特性

- ✅ Agent 多轮工具调用（cat, ls, find）
- ✅ OpenAI GPT-5-mini 模型支持
- ✅ Pydantic 结构化输出强制
- ✅ FastAPI 服务接口

## 安装

```bash
# 创建虚拟环境（如果还没有）
uv venv

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
uv pip install -r requirements.txt
# 或者如果网络有问题，可以尝试：
# pip install fastapi uvicorn openai pydantic python-dotenv
```

## 环境变量

确保设置了 OpenAI API Key：

```bash
export OPENAI_API_KEY="your-api-key-here"
```

## 运行服务

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动 FastAPI 服务（使用 8001 端口，因为 8000 被占用）
python -m uvicorn main:app --port 8001 --reload
```

服务将在 `http://localhost:8001` 启动。

## API 使用

### 查询端点

```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "列出当前目录下的所有 Python 文件",
    "model": "gpt-5-mini",
    "max_iterations": 6
  }'
```

### 响应格式

```json
{
  "answer": "根据查询结果，当前目录下有以下 Python 文件：...",
  "confidence": "high",
  "sources": ["main.py", "agent.py", "tools.py"],
  "reasoning": "使用了 ls 和 find 工具来查找文件"
}
```

## 测试

运行基础测试：

```bash
source .venv/bin/activate
python tests/test_mvp.py
```

## 项目结构

```
.
├── main.py              # FastAPI 服务入口
├── src/                 # 源代码目录
│   ├── agent.py         # Agent 核心逻辑
│   ├── indexing.py      # 代码索引服务
│   ├── search.py        # 代码搜索服务
│   ├── tools.py         # 工具函数（cat, ls, find）
│   └── models.py        # Pydantic 数据模型
├── frontend/            # React 前端应用
│   ├── src/             # 前端源代码
│   └── ...
├── tests/               # 测试脚本目录
│   ├── test_mvp.py      # MVP 测试脚本
│   ├── test_index.py    # 索引测试脚本
│   └── ...
├── self_index/          # 示例索引数据
├── docs/                # 文档
├── requirements.txt     # Python 依赖列表
├── launch_backend.sh    # 后端启动脚本
└── README.md            # 本文件
```

## 核心流程

1. **接收查询**: Agent 接收用户的自然语言问题
2. **多轮迭代**: Agent 可以调用工具（cat, ls, find）最多 N 轮
3. **工具执行**: 系统执行工具并返回结果给 Agent
4. **强制总结**: 最后一轮不再提供工具，Agent 必须给出最终答案
5. **结构化输出**: 最终答案必须符合 Pydantic FinalAnswer 模型

## 下一步

完成 MVP 验证后，将实现完整功能：
- FAISS 向量索引（文件索引和函数索引）
- 代码结构解析（LLM 驱动的函数识别）
- 语义搜索工具
- 完整的索引服务

