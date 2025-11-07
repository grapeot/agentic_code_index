"""Indexing service for codebase."""
import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
import faiss
import numpy as np

logger = logging.getLogger(__name__)


class CodeIndexer:
    """Index codebase with file and function level chunks."""
    
    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        parse_model: str = "gpt-5-mini",
        api_key: Optional[str] = None
    ):
        self.embedding_model = embedding_model
        self.parse_model = parse_model
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.supported_extensions = {'.py', '.js', '.ts', '.go', '.java', '.cpp', '.c', '.rs', '.rb', '.php'}
        
    def _get_supported_files(self, codebase_path: str) -> List[str]:
        """Get all supported source files from codebase."""
        files = []
        path = Path(codebase_path)
        
        for ext in self.supported_extensions:
            for file_path in path.rglob(f"*{ext}"):
                # Skip virtual environments and common ignore patterns
                if any(ignore in str(file_path) for ignore in ['.venv', 'node_modules', '__pycache__', '.git']):
                    continue
                files.append(str(file_path))
        
        return sorted(files)
    
    def _parse_functions(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Parse functions from a file using LLM."""
        prompt = f"""分析以下代码文件，识别出所有函数（包括类方法）。

文件路径: {file_path}

代码内容:
```
{content}
```

请返回一个 JSON 数组，每个元素包含：
- function_name: 函数名称
- start_line: 起始行号（从1开始）
- end_line: 结束行号（包含）

只返回 JSON 数组，不要其他文字。如果文件没有函数，返回空数组 []。"""

        try:
            response = self.client.chat.completions.create(
                model=self.parse_model,
                messages=[
                    {"role": "system", "content": "你是一个代码分析专家。只返回有效的 JSON 数组，不要其他解释。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "functions",
                        "strict": True,
                        "schema": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "function_name": {"type": "string"},
                                    "start_line": {"type": "integer"},
                                    "end_line": {"type": "integer"}
                                },
                                "required": ["function_name", "start_line", "end_line"],
                                "additionalProperties": False
                            },
                            "additionalProperties": False,
                            "required": []
                        }
                    }
                }
            )
            
            result = json.loads(response.choices[0].message.content)
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.warning(f"Failed to parse functions in {file_path}: {e}")
            return []
    
    def _create_chunks(self, file_path: str, content: str, functions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create file and function chunks."""
        chunks = []
        lines = content.split('\n')
        
        # File chunk
        chunks.append({
            "type": "file",
            "file_path": file_path,
            "content": content,
            "start_line": 1,
            "end_line": len(lines)
        })
        
        # Function chunks
        for func in functions:
            start = func["start_line"] - 1  # Convert to 0-based
            end = func["end_line"]
            func_content = '\n'.join(lines[start:end])
            
            chunks.append({
                "type": "function",
                "file_path": file_path,
                "function_name": func["function_name"],
                "content": func_content,
                "start_line": func["start_line"],
                "end_line": func["end_line"]
            })
        
        return chunks
    
    def _get_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings for a list of texts."""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings, dtype=np.float32)
    
    def index(self, codebase_path: str, output_dir: str = "index_data") -> Dict[str, Any]:
        """Index a codebase."""
        logger.info(f"🚀 Starting indexing for: {codebase_path}")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Get all files
        files = self._get_supported_files(codebase_path)
        logger.info(f"📁 Found {len(files)} files to index")
        
        all_chunks = []
        
        # Process each file
        for i, file_path in enumerate(files):
            logger.info(f"📄 Processing ({i+1}/{len(files)}): {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
                continue
            
            # Parse functions
            functions = self._parse_functions(file_path, content)
            logger.info(f"   Found {len(functions)} functions")
            
            # Create chunks
            chunks = self._create_chunks(file_path, content, functions)
            all_chunks.extend(chunks)
        
        logger.info(f"📦 Created {len(all_chunks)} chunks total")
        
        # Separate file and function chunks
        file_chunks = [c for c in all_chunks if c["type"] == "file"]
        function_chunks = [c for c in all_chunks if c["type"] == "function"]
        
        logger.info(f"   File chunks: {len(file_chunks)}")
        logger.info(f"   Function chunks: {len(function_chunks)}")
        
        # Get embeddings
        logger.info("🔢 Generating embeddings...")
        file_contents = [c["content"] for c in file_chunks]
        function_contents = [c["content"] for c in function_chunks]
        
        # Batch embeddings
        file_embeddings = self._get_embeddings(file_contents) if file_chunks else np.array([], dtype=np.float32)
        function_embeddings = self._get_embeddings(function_contents) if function_chunks else np.array([], dtype=np.float32)
        
        logger.info(f"   File embeddings shape: {file_embeddings.shape}")
        logger.info(f"   Function embeddings shape: {function_embeddings.shape}")
        
        # Build FAISS indices
        logger.info("🔨 Building FAISS indices...")
        
        if len(file_embeddings) > 0:
            dimension = file_embeddings.shape[1]
            file_index = faiss.IndexFlatL2(dimension)
            file_index.add(file_embeddings)
            faiss.write_index(file_index, str(output_path / "file_index.faiss"))
            logger.info(f"   ✓ Saved file index with {file_index.ntotal} vectors")
        
        if len(function_embeddings) > 0:
            dimension = function_embeddings.shape[1]
            function_index = faiss.IndexFlatL2(dimension)
            function_index.add(function_embeddings)
            faiss.write_index(function_index, str(output_path / "function_index.faiss"))
            logger.info(f"   ✓ Saved function index with {function_index.ntotal} vectors")
        
        # Save metadata
        metadata = {
            "codebase_path": codebase_path,
            "total_files": len(files),
            "total_chunks": len(all_chunks),
            "file_chunks": len(file_chunks),
            "function_chunks": len(function_chunks),
            "chunks": all_chunks
        }
        
        metadata_path = output_path / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Saved metadata to {metadata_path}")
        logger.info("✅ Indexing completed!")
        
        return {
            "status": "success",
            "total_files": len(files),
            "total_chunks": len(all_chunks),
            "file_chunks": len(file_chunks),
            "function_chunks": len(function_chunks),
            "output_dir": str(output_path)
        }

