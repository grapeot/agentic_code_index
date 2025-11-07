"""Indexing service for codebase."""
import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
import faiss
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
                # Skip virtual environments, test directories, and common ignore patterns
                if any(ignore in str(file_path) for ignore in ['.venv', 'node_modules', '__pycache__', '.git', 'tests/']):
                    continue
                files.append(str(file_path))
        
        return sorted(files)
    
    def _parse_functions(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Parse functions from a file using LLM."""
        logger.debug(f"   [PARSE] Starting function parsing for {file_path}")
        start_time = time.time()
        
        prompt = f"""分析以下代码文件，识别出所有函数（包括类方法）。

文件路径: {file_path}

代码内容:
```
{content}
```

请返回一个 JSON 对象，包含一个 "functions" 字段，值为函数数组。每个函数对象包含：
- function_name: 函数名称
- start_line: 起始行号（从1开始）
- end_line: 结束行号（包含）

只返回 JSON 对象，不要其他文字。如果文件没有函数，返回 {{"functions": []}}。"""

        try:
            logger.debug(f"   [PARSE] Sending API request for {file_path}")
            api_start = time.time()
            response = self.client.chat.completions.create(
                model=self.parse_model,
                messages=[
                    {"role": "system", "content": "你是一个代码分析专家。只返回有效的 JSON 对象，不要其他解释。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "function_parser",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {
                                "functions": {
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
                                    "additionalProperties": False
                                }
                            },
                            "required": ["functions"],
                            "additionalProperties": False
                        }
                    }
                }
            )
            api_time = time.time() - api_start
            logger.debug(f"   [PARSE] API response received for {file_path} (took {api_time:.2f}s)")
            
            logger.debug(f"   [PARSE] Parsing JSON response for {file_path}")
            result = json.loads(response.choices[0].message.content)
            functions = result.get("functions", [])
            functions = functions if isinstance(functions, list) else []
            
            total_time = time.time() - start_time
            logger.debug(f"   [PARSE] Completed parsing for {file_path}: {len(functions)} functions (total: {total_time:.2f}s)")
            return functions
        except Exception as e:
            total_time = time.time() - start_time
            logger.warning(f"   [PARSE] Failed to parse functions in {file_path} (took {total_time:.2f}s): {e}")
            import traceback
            logger.debug(traceback.format_exc())
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
        logger.debug(f"   [EMBED] Getting embeddings for {len(texts)} texts")
        start_time = time.time()
        
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=texts
        )
        
        embeddings = [item.embedding for item in response.data]
        elapsed = time.time() - start_time
        logger.debug(f"   [EMBED] Got embeddings (took {elapsed:.2f}s)")
        return np.array(embeddings, dtype=np.float32)
    
    def _process_single_file(self, file_path: str, file_index: int, total_files: int) -> List[Dict[str, Any]]:
        """Process a single file and return its chunks."""
        logger.info(f"📄 Processing ({file_index+1}/{total_files}): {file_path}")
        start_time = time.time()
        
        try:
            logger.debug(f"   [READ] Reading file {file_path}")
            read_start = time.time()
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            read_time = time.time() - read_start
            logger.debug(f"   [READ] Read file {file_path} ({len(content)} chars, took {read_time:.2f}s)")
            
            # Skip very large files to avoid timeout
            if len(content) > 50000:  # ~50KB
                logger.warning(f"   ⚠️  Skipping function parsing for large file ({len(content)} chars)")
                # Still create file chunk but skip function parsing
                chunks = [{
                    "type": "file",
                    "file_path": file_path,
                    "content": content,
                    "start_line": 1,
                    "end_line": len(content.split('\n'))
                }]
                elapsed = time.time() - start_time
                logger.info(f"   ✓ Completed {file_path} (took {elapsed:.2f}s, skipped function parsing)")
                return chunks
        except Exception as e:
            logger.warning(f"   ✗ Failed to read {file_path}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
        
        # Parse functions
        functions = []
        try:
            logger.debug(f"   [PARSE] Starting function parsing for {file_path}")
            functions = self._parse_functions(file_path, content)
            logger.info(f"   Found {len(functions)} functions")
        except Exception as e:
            logger.warning(f"   ✗ Failed to parse functions: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            functions = []
        
        # Create chunks
        logger.debug(f"   [CHUNK] Creating chunks for {file_path}")
        chunks = self._create_chunks(file_path, content, functions)
        elapsed = time.time() - start_time
        logger.info(f"   ✓ Completed {file_path} (took {elapsed:.2f}s, {len(chunks)} chunks)")
        return chunks
    
    def index(
        self, 
        codebase_path: str, 
        output_dir: str = "index_data",
        max_workers: int = 32
    ) -> Dict[str, Any]:
        """Index a codebase with parallel processing."""
        logger.info(f"🚀 Starting indexing for: {codebase_path}")
        logger.info(f"⚙️  Using {max_workers} parallel workers")
        total_start_time = time.time()
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        logger.info(f"📂 Output directory: {output_path}")
        
        # Get all files
        logger.info(f"🔍 Scanning for supported files...")
        scan_start = time.time()
        files = self._get_supported_files(codebase_path)
        scan_time = time.time() - scan_start
        logger.info(f"📁 Found {len(files)} files to index (scan took {scan_time:.2f}s)")
        if len(files) > 0:
            logger.info(f"   First few files: {files[:5]}")
        
        all_chunks = []
        
        # Process files in parallel
        logger.info(f"🔄 Starting parallel file processing...")
        process_start = time.time()
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self._process_single_file, file_path, i, len(files)): file_path
                for i, file_path in enumerate(files)
            }
            
            # Collect results as they complete
            completed = 0
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                completed += 1
                try:
                    chunks = future.result()
                    all_chunks.extend(chunks)
                    logger.info(f"   ✓ Progress: {completed}/{len(files)} files processed")
                except Exception as e:
                    logger.error(f"   ✗ File {file_path} generated an exception: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
        
        process_time = time.time() - process_start
        logger.info(f"✅ File processing completed (took {process_time:.2f}s)")
        
        logger.info(f"📦 Created {len(all_chunks)} chunks total")
        
        # Separate file and function chunks
        file_chunks = [c for c in all_chunks if c["type"] == "file"]
        function_chunks = [c for c in all_chunks if c["type"] == "function"]
        
        logger.info(f"   File chunks: {len(file_chunks)}")
        logger.info(f"   Function chunks: {len(function_chunks)}")
        
        # Get embeddings in batches
        logger.info("🔢 Generating embeddings...")
        embed_start = time.time()
        file_contents = [c["content"] for c in file_chunks]
        function_contents = [c["content"] for c in function_chunks]
        
        # Batch embeddings (OpenAI supports up to 2048 items per batch)
        batch_size = 100
        file_embeddings_list = []
        if file_chunks:
            total_batches = (len(file_contents) - 1) // batch_size + 1
            logger.info(f"   Processing {len(file_contents)} file chunks in {total_batches} batches...")
            for i in range(0, len(file_contents), batch_size):
                batch = file_contents[i:i+batch_size]
                batch_num = i // batch_size + 1
                logger.info(f"   [EMBED] Processing file embeddings batch {batch_num}/{total_batches} ({len(batch)} items)")
                batch_start = time.time()
                batch_embeddings = self._get_embeddings(batch)
                batch_time = time.time() - batch_start
                file_embeddings_list.append(batch_embeddings)
                logger.info(f"   [EMBED] Batch {batch_num} completed (took {batch_time:.2f}s)")
            file_embeddings = np.vstack(file_embeddings_list) if file_embeddings_list else np.array([], dtype=np.float32)
        else:
            file_embeddings = np.array([], dtype=np.float32)
        
        function_embeddings_list = []
        if function_chunks:
            total_batches = (len(function_contents) - 1) // batch_size + 1
            logger.info(f"   Processing {len(function_contents)} function chunks in {total_batches} batches...")
            for i in range(0, len(function_contents), batch_size):
                batch = function_contents[i:i+batch_size]
                batch_num = i // batch_size + 1
                logger.info(f"   [EMBED] Processing function embeddings batch {batch_num}/{total_batches} ({len(batch)} items)")
                batch_start = time.time()
                batch_embeddings = self._get_embeddings(batch)
                batch_time = time.time() - batch_start
                function_embeddings_list.append(batch_embeddings)
                logger.info(f"   [EMBED] Batch {batch_num} completed (took {batch_time:.2f}s)")
            function_embeddings = np.vstack(function_embeddings_list) if function_embeddings_list else np.array([], dtype=np.float32)
        else:
            function_embeddings = np.array([], dtype=np.float32)
        
        embed_time = time.time() - embed_start
        logger.info(f"   File embeddings shape: {file_embeddings.shape}")
        logger.info(f"   Function embeddings shape: {function_embeddings.shape}")
        logger.info(f"   Embedding generation took {embed_time:.2f}s")
        
        # Build FAISS indices
        logger.info("🔨 Building FAISS indices...")
        index_start = time.time()
        
        if len(file_embeddings) > 0:
            dimension = file_embeddings.shape[1]
            logger.debug(f"   Creating file index with dimension {dimension}")
            file_index = faiss.IndexFlatL2(dimension)
            file_index.add(file_embeddings)
            index_file = output_path / "file_index.faiss"
            logger.debug(f"   Writing file index to {index_file}")
            faiss.write_index(file_index, str(index_file))
            logger.info(f"   ✓ Saved file index with {file_index.ntotal} vectors")
        
        if len(function_embeddings) > 0:
            dimension = function_embeddings.shape[1]
            logger.debug(f"   Creating function index with dimension {dimension}")
            function_index = faiss.IndexFlatL2(dimension)
            function_index.add(function_embeddings)
            index_file = output_path / "function_index.faiss"
            logger.debug(f"   Writing function index to {index_file}")
            faiss.write_index(function_index, str(index_file))
            logger.info(f"   ✓ Saved function index with {function_index.ntotal} vectors")
        
        index_time = time.time() - index_start
        logger.info(f"   Index building took {index_time:.2f}s")
        
        # Save metadata
        logger.info("💾 Saving metadata...")
        metadata_start = time.time()
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
        
        metadata_time = time.time() - metadata_start
        logger.info(f"   ✓ Saved metadata to {metadata_path} (took {metadata_time:.2f}s)")
        
        total_time = time.time() - total_start_time
        logger.info(f"✅ Indexing completed! Total time: {total_time:.2f}s")
        logger.info(f"   Summary:")
        logger.info(f"     - Files: {len(files)}")
        logger.info(f"     - File chunks: {len(file_chunks)}")
        logger.info(f"     - Function chunks: {len(function_chunks)}")
        logger.info(f"     - Total chunks: {len(all_chunks)}")
        
        return {
            "status": "success",
            "total_files": len(files),
            "total_chunks": len(all_chunks),
            "file_chunks": len(file_chunks),
            "function_chunks": len(function_chunks),
            "output_dir": str(output_path)
        }

