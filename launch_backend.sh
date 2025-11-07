#!/bin/bash
# Launch backend server with auto-reload for development

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠ Warning: OPENAI_API_KEY is not set in environment"
    echo "   The server will start but queries may fail"
fi

# Start uvicorn with reload
echo "Starting FastAPI server on port 8001 with auto-reload..."
echo "API docs available at: http://localhost:8001/docs"
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload

