# SHL Conversational Assessment Agent - Approach Document

## 1. System Architecture
The application is built as a stateless, highly performant web service using **FastAPI**. It adheres strictly to the non-negotiable API schemas (`/health` and `/chat`) and operates with a sub-second response time architecture.

The core pipeline consists of three components:
1. **Catalog & Retrieval Engine (scikit-learn):** A hybrid retrieval system that combines TF-IDF semantic matching with structured metadata boosting (categories, job levels).
2. **Prompt Builder:** A dynamic context assembler that injects conversation history and the top `N` candidate assessments into the LLM prompt.
3. **LLM Orchestration (Groq & Gemini):** A resilient, cascading LLM router that processes the prompt, enforces JSON schema compliance, and implements strict behavioral guardrails.

## 2. Retrieval Strategy: Hybrid TF-IDF and Metadata Matching
To ensure accurate recommendations from the 377-item SHL catalog, the agent employs a lightweight, in-memory retrieval engine rather than a heavy vector database.

*   **Initialization:** At startup, the catalog is parsed, and descriptions, names, and tags are concatenated into a `search_text` blob. `TfidfVectorizer` (from scikit-learn) computes a sparse embedding matrix for the entire catalog.
*   **Query Processing:** User messages are extracted and combined to form the search query.
*   **Scoring & Boosting:** The query is transformed via TF-IDF, and cosine similarity is calculated against all catalog items. Crucially, the system utilizes **metadata boosting**: if a user mentions specific keywords (e.g., "developer," "personality," "cognitive"), corresponding catalog categories are heavily boosted in the final score.
*   **Efficiency:** This approach is fully synchronous, requires no external database connections, and executes in milliseconds, ensuring the system stays well within the 30-second timeout constraint.

## 3. Large Language Model (LLM) Strategy & Resilience
The agent requires deep semantic understanding of both the user's intent and the intricate nuances of SHL assessments (e.g., distinguishing between OPQ32r and Verify G+).

*   **Primary Model:** The system utilizes **Groq's Llama-3.3-70b-versatile** as the primary engine. Groq's LPU architecture guarantees blazing-fast inference speeds, allowing the agent to process the conversation history and 20+ candidate assessments within 2-3 seconds.
*   **Model Cascade (Circuit Breaker Pattern):** To mitigate API rate limits during heavy load, the agent implements a multi-tiered fallback cascade:
    1.  `llama-3.3-70b-versatile` (Groq Primary)
    2.  `llama-3.1-8b-instant` (Groq Fallback)
    3.  `gemini-2.0-flash` (Google Fallback with a 5-minute cooldown circuit breaker on 429 Quota Exceeded errors).
*   **JSON Enforcement:** The LLMs are explicitly configured to output native JSON (`response_format={"type": "json_object"}`), which is then parsed and strictly validated against Pydantic models (`ChatResponse`, `Recommendation`) to guarantee 100% schema compliance for the automated evaluator.

## 4. Prompt Engineering & Behavioral Guardrails
The system prompt is the central brain of the agent, dictating exactly *how* and *when* to respond. 

*   **Aggressive Recommendation:** A common failure mode for conversational agents is over-clarifying. The prompt is engineered with a **"RECOMMEND FIRST"** directive. If the user mentions a job title or specific skill, the agent immediately provides a grounded shortlist (including defaults like OPQ32r) rather than wasting the 8-turn limit on clarification.
*   **Strict Catalog Grounding:** The prompt enforces that the LLM may *only* recommend items explicitly provided in the `## CATALOG CANDIDATES` context block. If a requested skill isn't in the catalog, the agent is instructed to suggest the closest alternatives rather than hallucinating URLs.
*   **Guardrails:** Explicit instructions are included to refuse off-topic inquiries (e.g., legal HR advice or prompt injections). The agent responds politely but firmly, setting `recommendations: null`.

## 5. Known Limitations & Future Improvements
*   **Context Window Limits:** Currently, the retriever limits candidates to ~25 items and truncates descriptions to 150 characters to prevent Groq API token limit exhaustion. A future improvement would involve chunking the catalog descriptions or utilizing a model with a natively larger context window to allow the LLM to see the entire catalog simultaneously.
*   **Statelessness Overhead:** Because the `/chat` endpoint is strictly stateless, the entire conversation history must be re-processed on every turn. As conversations approach the 8-turn limit, the prompt size grows significantly. Implementing a fast semantic caching layer (like Redis) could cache previous LLM thoughts to reduce latency on turns 4-8.
