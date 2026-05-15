# SHL Conversational Assessment Agent

A conversational AI agent that helps hiring managers and recruiters discover the right SHL Individual Test Solutions through natural dialogue. Built as a stateless FastAPI service.

## 🚀 Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd SHL-assignmnet

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### `GET /health`
Returns `{"status": "ok"}` with HTTP 200.

### `POST /chat`
Stateless conversation endpoint.

**Request:**
```json
{
  "messages": [
    {"role": "user", "content": "I'm hiring a Java developer"},
    {"role": "assistant", "content": "What seniority level?"},
    {"role": "user", "content": "Mid-level, around 4 years"}
  ]
}
```

**Response:**
```json
{
  "reply": "Here are 5 assessments that fit...",
  "recommendations": [
    {"name": "Core Java (Advanced Level) (New)", "url": "https://www.shl.com/...", "test_type": "K"},
    {"name": "OPQ32r", "url": "https://www.shl.com/...", "test_type": "P"}
  ],
  "end_of_conversation": false
}
```

## 🏗️ Architecture

```
POST /chat → FastAPI → Retriever (TF-IDF + metadata filters) → LLM (Gemini/Groq) → Validated Response
```

- **Catalog**: 377 SHL Individual Test Solutions loaded from JSON at startup
- **Retrieval**: Hybrid TF-IDF text search + structured metadata matching + category boosting
- **LLM**: Gemini 2.0 Flash (primary) with Groq fallback (llama-3.3-70b → llama-3.1-8b → gemma2-9b)
- **Validation**: Every recommendation URL verified against the scraped catalog

## 🧠 Conversational Behaviors

| Behavior | Description |
|----------|-------------|
| **Clarify** | Asks follow-up questions for vague queries before recommending |
| **Recommend** | Provides 1-10 assessments with names, URLs, and test type codes |
| **Refine** | Updates shortlist when user changes constraints mid-conversation |
| **Compare** | Produces grounded comparisons from catalog data |
| **Guardrails** | Refuses off-topic, legal questions, and prompt injection attempts |

## 🔑 Test Type Codes

| Code | Category |
|------|----------|
| K | Knowledge & Skills |
| P | Personality & Behavior |
| A | Ability & Aptitude |
| B | Biodata & Situational Judgment |
| S | Simulations |
| C | Competencies |
| D | Development & 360 |

## 📦 Tech Stack

- **Framework**: FastAPI + Pydantic
- **Retrieval**: scikit-learn TF-IDF (lightweight, fast)
- **LLM**: Google Gemini 2.0 Flash / Groq (Llama 3.3)
- **Deployment**: Docker + Render

## 🚀 Deployment

Deploy to Render:
1. Push to GitHub
2. Connect repo to Render
3. Set environment variables (`GEMINI_API_KEY`, `GROQ_API_KEY`)
4. Deploy — Render uses the `Dockerfile` automatically
