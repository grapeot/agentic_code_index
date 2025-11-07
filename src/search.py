"""Search service for indexed codebase."""
import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
import faiss
import numpy as np

logger = logging.getLogger(__name__)


class CodeSearcher:
    """Search indexed codebase using FAISS."""
    
    def __init__(
        self,
        index_dir: str = "self_index",
        embedding_model: str = "text-embedding-3-small",
        api_key: Optional[str] = None
    ):
        self.index_dir = Path(index_dir)
        self.embedding_model = embedding_model
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        
        self.file_index = None
        self.function_index = None
        self.metadata = None
        
        self._load_indices()
    
    def _load_indices(self):
        """Load FAISS indices and metadata."""
        try:
            # Load metadata
            metadata_path = self.index_dir / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                logger.info(f"📂 Loaded metadata with {len(self.metadata.get('chunks', []))} chunks")
            else:
                logger.warning(f"Metadata file not found: {metadata_path}")
                return
            
            # Load file index
            file_index_path = self.index_dir / "file_index.faiss"
            if file_index_path.exists():
                self.file_index = faiss.read_index(str(file_index_path))
                logger.info(f"📁 Loaded file index with {self.file_index.ntotal} vectors")
            
            # Load function index
            function_index_path = self.index_dir / "function_index.faiss"
            if function_index_path.exists():
                self.function_index = faiss.read_index(str(function_index_path))
                logger.info(f"🔧 Loaded function index with {self.function_index.ntotal} vectors")
                
        except Exception as e:
            logger.error(f"Failed to load indices: {e}")
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for a single text."""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=[text]
        )
        return np.array([response.data[0].embedding], dtype=np.float32)
    
    def search(self, question: str, index_type: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search the indexed codebase."""
        if not self.metadata:
            return []
        
        # Get query embedding
        query_embedding = self._get_embedding(question)
        
        # Select index
        if index_type == "file":
            index = self.file_index
            chunk_type = "file"
        elif index_type == "function":
            index = self.function_index
            chunk_type = "function"
        else:
            logger.error(f"Invalid index_type: {index_type}")
            return []
        
        if index is None or index.ntotal == 0:
            logger.warning(f"Index {index_type} is not available or empty")
            return []
        
        # Search
        distances, indices = index.search(query_embedding, min(top_k, index.ntotal))
        
        # Get results
        results = []
        chunks = self.metadata.get("chunks", [])
        
        # Filter chunks by type
        typed_chunks = [c for c in chunks if c.get("type") == chunk_type]
        
        for i, idx in enumerate(indices[0]):
            if idx < len(typed_chunks):
                chunk = typed_chunks[idx]
                result = {
                    "file_path": chunk.get("file_path"),
                    "content": chunk.get("content"),
                    "distance": float(distances[0][i]),
                    "type": chunk_type
                }
                
                if chunk_type == "function":
                    result["function_name"] = chunk.get("function_name")
                    result["start_line"] = chunk.get("start_line")
                    result["end_line"] = chunk.get("end_line")
                else:
                    result["start_line"] = chunk.get("start_line", 1)
                    result["end_line"] = chunk.get("end_line", len(chunk.get("content", "").split('\n')))
                
                results.append(result)
        
        logger.info(f"🔍 Found {len(results)} results for '{question}' in {index_type} index")
        return results
    
    def list_file_content(self, file_path: str) -> str:
        """Get full content of a file from metadata."""
        if not self.metadata:
            return ""
        
        chunks = self.metadata.get("chunks", [])
        for chunk in chunks:
            if chunk.get("type") == "file" and chunk.get("file_path") == file_path:
                return chunk.get("content", "")
        
        # If not in metadata, try to read from filesystem
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""

