"""Pydantic models for structured output."""
from pydantic import BaseModel, Field
from typing import List, Optional


class FinalAnswer(BaseModel):
    """Final answer from the agent."""
    answer: str = Field(description="The comprehensive answer to the user's question")
    confidence: str = Field(
        description="Confidence level: 'high', 'medium', or 'low'",
        pattern="^(high|medium|low)$"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="List of file paths or tool results that were used to generate this answer"
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="Brief explanation of the reasoning process"
    )

