"""FastAPI server for the code indexing agent."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import os
import logging
import re
from pathlib import Path

from src.agent import Agent
from src.models import FinalAnswer
from src.indexing import CodeIndexer
from src.search import CodeSearcher
from src.tools import set_searcher


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

# 创建 API 路由组（用于前端 /api 前缀）
from fastapi import APIRouter
api_router = APIRouter()

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


@api_router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Code Indexing Agent",
        "version": "1.0.0",
        "endpoints": {
            "/api/index": "POST - Index a codebase",
            "/api/query": "POST - Query the agent with a question",
            "/api/health": "GET - Health check"
        },
        "index_loaded": searcher is not None
    }


@api_router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@api_router.get("/file")
async def get_file(file_path: str):
    """Get file content."""
    from src.tools import cat_file
    
    result = cat_file(file_path)
    
    if result["success"]:
        return {"content": result["content"]}
    else:
        raise HTTPException(status_code=404, detail=result.get("error", "File not found"))


@api_router.get("/files")
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


@api_router.get("/file-tree")
async def get_file_tree(root_path: str = "."):
    """Get real filesystem directory structure."""
    import os
    from pathlib import Path
    
    def build_tree(path: Path, base_path: Path):
        """Recursively build file tree structure."""
        result = {
            "name": path.name if path != base_path else ".",
            "path": str(path.relative_to(base_path)) if path != base_path else ".",
            "type": "directory",
            "children": []
        }
        
        try:
            # Skip hidden directories and common ignore patterns
            skip_patterns = ['.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache']
            if any(pattern in path.name for pattern in skip_patterns):
                return None
            
            if path.is_dir():
                try:
                    items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                    for item in items:
                        # Skip hidden files and directories
                        if item.name.startswith('.'):
                            continue
                        
                        # Skip ignore patterns
                        if any(pattern in item.name for pattern in skip_patterns):
                            continue
                        
                        if item.is_file():
                            # Only include supported code files
                            supported_extensions = {'.py', '.js', '.ts', '.go', '.java', '.cpp', '.c', '.rs', '.rb', '.php', '.md', '.json', '.yaml', '.yml', '.html', '.css'}
                            if item.suffix in supported_extensions:
                                result["children"].append({
                                    "name": item.name,
                                    "path": str(item.relative_to(base_path)),
                                    "type": "file"
                                })
                        elif item.is_dir():
                            child_tree = build_tree(item, base_path)
                            if child_tree:
                                result["children"].append(child_tree)
                except PermissionError:
                    pass
        except Exception as e:
            print(f"Error building tree for {path}: {e}")
        
        return result
    
    try:
        root = Path(root_path).resolve()
        if not root.exists():
            return {"error": f"Path does not exist: {root_path}"}
        
        tree = build_tree(root, root)
        return tree if tree else {"error": "Failed to build file tree"}
    except Exception as e:
        return {"error": str(e)}


@api_router.post("/index", response_model=IndexResponse)
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


@api_router.post("/query", response_model=QueryResponse)
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


# 注册 API 路由（只使用 /api 前缀，根路径留给前端）
app.include_router(api_router, prefix="/api", tags=["api"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Serve frontend static files if they exist (must be after all API routes)
frontend_dist = Path("frontend/dist")

if frontend_dist.exists():
    # Mount static assets
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    @app.get("/")
    async def serve_frontend_root(request: Request):
        """Serve frontend index.html for root path."""
        index_file = frontend_dist / "index.html"
        
        if index_file.exists():
            # Read HTML content
            html_content = index_file.read_text(encoding='utf-8')
            
            # Try to get base path from various sources
            base_path = ""
            
            # 1. Check X-Forwarded-Path header (Koyeb might set this)
            forwarded_path = request.headers.get("X-Forwarded-Path") or request.headers.get("X-Original-Path")
            if forwarded_path:
                base_path = forwarded_path.rstrip('/')
            
            # 2. Check request URL host/path (might contain service name)
            if not base_path:
                host = request.headers.get("Host", "")
                if "koyeb.app" in host:
                    env_base_path = os.getenv("BASE_PATH", "")
                    if env_base_path:
                        base_path = env_base_path.rstrip('/')
            
            # 3. If still no base_path, check if request path is not root
            if not base_path:
                request_path = request.url.path.rstrip('/')
                if request_path and request_path != '/':
                    base_path = request_path
            
            if base_path:
                # Replace absolute paths with base path
                html_content = re.sub(r'href="/assets/', f'href="{base_path}/assets/', html_content)
                html_content = re.sub(r'src="/assets/', f'src="{base_path}/assets/', html_content)
            
            return HTMLResponse(content=html_content)
        else:
            raise HTTPException(status_code=404, detail="Frontend not found")
    
    @app.get("/{path:path}")
    async def serve_frontend(path: str, request: Request):
        """Serve frontend files, fallback to index.html for SPA routing."""
        # Skip API routes and docs
        if path.startswith(("api/", "docs", "openapi.json")):
            raise HTTPException(status_code=404)
        
        file_path = frontend_dist / path
        
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # For SPA routing, return index.html
        index_file = frontend_dist / "index.html"
        
        if index_file.exists():
            # Read HTML content
            html_content = index_file.read_text(encoding='utf-8')
            
            # Try to get base path from various sources
            base_path = ""
            
            # 1. Check X-Forwarded-Path header (Koyeb might set this)
            forwarded_path = request.headers.get("X-Forwarded-Path") or request.headers.get("X-Original-Path")
            if forwarded_path:
                base_path = forwarded_path.rstrip('/')
            
            # 2. Check BASE_PATH env var (set by deploy script)
            if not base_path:
                env_base_path = os.getenv("BASE_PATH", "")
                if env_base_path:
                    base_path = env_base_path.rstrip('/')
            
            # 3. Check request URL path
            if not base_path:
                request_path = request.url.path.rstrip('/')
                if request_path and request_path != '/' and not request_path.startswith(('/api', '/docs', '/openapi.json', '/assets')):
                    # Check if this looks like a service path
                    path_parts = [p for p in request_path.split('/') if p]
                    if len(path_parts) == 1 and not path_parts[0].endswith(('.html', '.js', '.css', '.png', '.jpg', '.svg')):
                        base_path = request_path
            
            if base_path:
                # Replace absolute paths with base path
                html_content = re.sub(r'href="/assets/', f'href="{base_path}/assets/', html_content)
                html_content = re.sub(r'src="/assets/', f'src="{base_path}/assets/', html_content)
            
            return HTMLResponse(content=html_content)
        
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
else:
    # Register root route even if frontend doesn't exist, so we can show helpful error
    @app.get("/")
    async def serve_frontend_root_missing():
        """Serve error message when frontend is not found."""
        raise HTTPException(status_code=404, detail="Frontend not found")
    
    @app.get("/{path:path}")
    async def serve_frontend_missing(path: str):
        """Serve error message when frontend is not found."""
        if path.startswith(("api/", "docs", "openapi.json")):
            raise HTTPException(status_code=404)
        raise HTTPException(status_code=404, detail="Frontend not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

