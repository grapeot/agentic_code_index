#!/bin/bash
# Launch full-stack application (backend + frontend)
# This script builds the frontend and starts the FastAPI server

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🚀 Starting Code Indexing Agent..."
echo ""

# 1. Setup Python virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating Python virtual environment..."
    if command -v uv &> /dev/null; then
        uv venv
    else
        echo "⚠️  uv not found, using python3 -m venv"
        python3 -m venv .venv
    fi
fi

echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# 2. Install Python dependencies
if [ ! -f ".venv/.deps_installed" ] || [ requirements.txt -nt .venv/.deps_installed ]; then
    echo "📥 Installing Python dependencies..."
    if command -v uv &> /dev/null; then
        uv pip install -r requirements.txt
    else
        pip install -r requirements.txt
    fi
    touch .venv/.deps_installed
else
    echo "✅ Python dependencies already installed"
fi

# 3. Check OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY is not set in environment"
    echo "   The server will start but queries may fail"
    echo ""
fi

# 4. Setup and build frontend
if [ -d "frontend" ]; then
    cd frontend
    
    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        echo "⚠️  Warning: package.json not found in frontend directory"
        echo "   Skipping frontend build"
        cd ..
    else
        # Check if node_modules exists
        if [ ! -d "node_modules" ]; then
            echo "📦 Installing frontend dependencies..."
            npm install
        else
            echo "✅ Frontend dependencies already installed"
        fi
        
        # Build frontend
        echo "🔨 Building frontend..."
        npm run build
        
        cd ..
    fi
else
    echo "⚠️  Warning: frontend directory not found, skipping frontend build"
fi

# 5. Start FastAPI server
echo ""
echo "🌟 Starting FastAPI server on port 8001..."
echo "   - API docs: http://localhost:8001/docs"
echo "   - Frontend: http://localhost:8001/"
echo "   - Health check: http://localhost:8001/api/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# ⚠️ 重要：必须使用 --host 0.0.0.0 而不是 127.0.0.1 或 localhost
# 0.0.0.0 绑定所有网络接口，允许从外部访问（Docker、容器、远程访问等）
# 127.0.0.1 和 localhost 只绑定本地回环接口，只能从本机访问
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

