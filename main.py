"""FastAPI server for the code indexing agent."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from agent import Agent
from models import FinalAnswer


app = FastAPI(title="Code Indexing Agent MVP", version="0.1.0")


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


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Code Indexing Agent MVP",
        "version": "0.1.0",
        "endpoints": {
            "/query": "POST - Query the agent with a question",
            "/health": "GET - Health check"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


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

