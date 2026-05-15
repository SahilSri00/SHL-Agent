"""
FastAPI service for the SHL Conversational Assessment Agent.
Two endpoints: GET /health and POST /chat.
"""

import os
import time
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import ChatRequest, ChatResponse
from app.catalog import Catalog
from app.retriever import Retriever
from app.agent import Agent


# ── Global state ─────────────────────────────────────────────────────────
agent: Agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize catalog, retriever, and agent on startup."""
    global agent

    print("[Startup] Loading SHL catalog...")
    start = time.time()

    catalog = Catalog()
    retriever = Retriever(catalog)
    agent = Agent(catalog, retriever)

    elapsed = time.time() - start
    print(f"[Startup] Ready in {elapsed:.1f}s")

    yield

    print("[Shutdown] Cleaning up...")


# ── FastAPI app ──────────────────────────────────────────────────────────
app = FastAPI(
    title="SHL Assessment Agent",
    description="Conversational agent for recommending SHL Individual Test Solutions",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for the evaluator
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Readiness check. Returns {"status": "ok"} with HTTP 200."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Stateless chat endpoint.
    Takes full conversation history, returns next agent reply with optional recommendations.
    """
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    if not request.messages:
        raise HTTPException(status_code=400, detail="messages must not be empty")

    # Enforce turn cap: max 8 turns
    if len(request.messages) > 8:
        # Still respond, but signal end
        return ChatResponse(
            reply="We've reached the maximum number of turns for this conversation. Based on our discussion, here's my final recommendation.",
            recommendations=None,
            end_of_conversation=True,
        )

    response = await agent.chat(request.messages)
    return response


# ── Run directly ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
