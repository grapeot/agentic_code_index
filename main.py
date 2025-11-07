"""FastAPI server for the code indexing agent."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import os

from agent import Agent
from models import FinalAnswer
from indexing import CodeIndexer
from search import CodeSearcher
from tools import set_searcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize searcher on startup if index exists."""
    global searcher
    # Default to self_index if it exists, otherwise use index_data or INDEX_DIR env var
    index_dir = os.getenv("INDEX_DIR", "self_index" if os.path.exists("self_index") and os.path.exists("self_index/metadata.json") else "index_data")
    if os.path.exists(index_dir) and os.path.exists(os.path.join(index_dir, "metadata.json")):
        try:
            searcher = CodeSearcher(index_dir=index_dir)
            set_searcher(searcher)
            print(f"✅ Loaded index from {index_dir}")
        except Exception as e:
            print(f"⚠️  Failed to load index: {e}")
    yield

app = FastAPI(title="Code Indexing Agent", version="1.0.0", lifespan=lifespan)

# Global searcher instance
searcher: Optional[CodeSearcher] = None


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    question: str
    model: Optional[str] = "gpt-5-mini"
    max_iterations: Optional[int] = 6


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    answer: str
    confidence: str
    sources: list[str]
    reasoning: Optional[str] = None


class IndexRequest(BaseModel):
    """Request model for index endpoint."""
    codebase_path: str
    output_dir: Optional[str] = "index_data"


class IndexResponse(BaseModel):
    """Response model for index endpoint."""
    status: str
    total_files: int
    total_chunks: int
    file_chunks: int
    function_chunks: int
    output_dir: str


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Code Indexing Agent",
        "version": "1.0.0",
        "endpoints": {
            "/index": "POST - Index a codebase",
            "/query": "POST - Query the agent with a question",
            "/health": "GET - Health check"
        },
        "index_loaded": searcher is not None
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/file")
async def get_file(file_path: str):
    """Get file content."""
    from tools import cat_file
    
    result = cat_file(file_path)
    
    if result["success"]:
        return {"content": result["content"]}
    else:
        raise HTTPException(status_code=404, detail=result.get("error", "File not found"))


@app.get("/files")
async def list_files():
    """List all indexed files."""
    global searcher
    if searcher is None or searcher.metadata is None:
        return {"files": []}
    
    files = set()
    for chunk in searcher.metadata.get("chunks", []):
        if chunk.get("type") == "file":
            files.add(chunk.get("file_path"))
    
    return {"files": sorted(list(files))}


@app.post("/index", response_model=IndexResponse)
async def index_codebase(request: IndexRequest):
    """Index a codebase."""
    try:
        indexer = CodeIndexer()
        result = indexer.index(request.codebase_path, request.output_dir)
        
        # Reload searcher with new index
        global searcher
        searcher = CodeSearcher(index_dir=request.output_dir)
        set_searcher(searcher)
        
        return IndexResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the agent with a question."""
    try:
        agent = Agent(
            model=request.model,
            max_iterations=request.max_iterations
        )
        result: FinalAnswer = agent.query(request.question)
        
        return QueryResponse(
            answer=result.answer,
            confidence=result.confidence,
            sources=result.sources,
            reasoning=result.reasoning
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent query failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

