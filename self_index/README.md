# Self Index

这个目录包含了当前代码库的索引数据，用于代码搜索和查询功能。

## 文件说明

- `file_index.faiss` - 文件级别的向量索引
- `function_index.faiss` - 函数级别的向量索引  
- `metadata.json` - 索引元数据，包含所有代码块的信息

## 索引信息

这个索引是通过 `CodeIndexer` 自动生成的，包含：
- 文件级别的代码块：整个文件的内容
- 函数级别的代码块：每个函数/方法的独立代码块

## 使用方法

索引会在服务启动时自动加载。如果需要重新生成索引，可以：

1. 通过 API 端点：
```bash
curl -X POST http://localhost:8001/index \
  -H "Content-Type: application/json" \
  -d '{"codebase_path": ".", "output_dir": "self_index"}'
```

2. 使用 Python 脚本：
```python
from indexing import CodeIndexer

indexer = CodeIndexer()
result = indexer.index('.', 'self_index', max_workers=32)
```

## 注意事项

- 索引文件会随着代码库的变化而过时，需要定期更新
- 索引生成需要调用 OpenAI API，会产生费用
- 建议将索引文件添加到 `.gitignore`（但这里作为示例保留）

