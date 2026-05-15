"""
Pydantic models for the SHL Chat API.
Schema is NON-NEGOTIABLE — any deviation breaks the automated evaluator.
"""

from pydantic import BaseModel, Field
from typing import Optional


class ChatMessage(BaseModel):
    """A single message in the conversation."""
    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str = Field(..., description="The message text")


class ChatRequest(BaseModel):
    """Stateless chat request carrying full conversation history."""
    messages: list[ChatMessage] = Field(..., description="Full conversation history")


class Recommendation(BaseModel):
    """A single assessment recommendation with catalog data."""
    name: str = Field(..., description="Assessment name from catalog")
    url: str = Field(..., description="Catalog URL — must come from scraped catalog")
    test_type: str = Field(..., description="Letter code(s): K, P, A, B, S, C, D, E")


class ChatResponse(BaseModel):
    """
    Response from the agent.
    - recommendations is None/null when agent is still gathering context or refusing.
    - recommendations is a list of 1-10 items when agent commits to a shortlist.
    - end_of_conversation is true only when agent considers the task complete.
    """
    reply: str = Field(..., description="Agent's text reply")
    recommendations: Optional[list[Recommendation]] = Field(
        None, description="1-10 assessment recommendations, or null"
    )
    end_of_conversation: bool = Field(
        False, description="True only when agent considers task complete"
    )
