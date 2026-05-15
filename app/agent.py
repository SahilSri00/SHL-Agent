"""
Agent orchestration — ties together retrieval and LLM to produce responses.
Supports Gemini (primary) and Groq (fallback) with retry logic.
"""

import json
import os
import re
import time
import traceback
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from app.catalog import Catalog, CatalogItem
from app.retriever import Retriever
from app.models import ChatMessage, ChatResponse, Recommendation
from app.prompts import SYSTEM_PROMPT, build_prompt


class Agent:
    """SHL Conversational Assessment Agent."""

    def __init__(self, catalog: Catalog, retriever: Retriever):
        self.catalog = catalog
        self.retriever = retriever
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM client(s). Gemini primary, Groq fallback."""
        self.gemini_model = None
        self.groq_client = None

        # Try Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                self.gemini_model = genai.GenerativeModel(
                    "gemini-2.0-flash",
                    system_instruction=SYSTEM_PROMPT,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                        max_output_tokens=2048,
                    ),
                )
                print("[Agent] Gemini 2.0 Flash initialized")
            except Exception as e:
                print(f"[Agent] Gemini init failed: {e}")

        # Try Groq
        groq_key = os.environ.get("GROQ_API_KEY", "").strip()
        if groq_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_key)
                print("[Agent] Groq client initialized (fallback)")
            except Exception as e:
                print(f"[Agent] Groq init failed: {e}")

        if not self.gemini_model and not self.groq_client:
            print("[Agent] WARNING: No LLM configured! Set GEMINI_API_KEY or GROQ_API_KEY")

    async def chat(self, messages: list[ChatMessage]) -> ChatResponse:
        """
        Process a stateless chat request.

        Args:
            messages: Full conversation history

        Returns:
            ChatResponse with reply, recommendations, and end_of_conversation
        """
        try:
            # Convert messages to dicts for retrieval
            msg_dicts = [{"role": m.role, "content": m.content} for m in messages]

            # Retrieve candidate assessments
            candidates = self.retriever.retrieve(msg_dicts)

            # Build candidate text blocks for the prompt
            candidate_texts = []
            for item in candidates:
                text = item.compact_repr() + f"\n  URL: {item.link}"
                candidate_texts.append(text)

            # Build the full prompt
            prompt = build_prompt(msg_dicts, candidate_texts)

            # Call LLM
            raw_response = await self._call_llm(prompt)

            # Parse and validate the response
            response = self._parse_response(raw_response)

            return response

        except Exception as e:
            print(f"[Agent] Error: {traceback.format_exc()}")
            # Return a safe fallback response that still matches schema
            return ChatResponse(
                reply="I apologize, but I encountered an issue processing your request. Could you please rephrase your question about SHL assessments?",
                recommendations=None,
                end_of_conversation=False,
            )

    async def _call_llm(self, prompt: str) -> str:
        """Call the LLM. Try Gemini first with retries, then Groq fallback."""
        last_error = None

        # Try Gemini (single attempt — if quota exceeded, fall through to Groq)
        if self.gemini_model:
            try:
                response = self.gemini_model.generate_content(prompt)
                return response.text
            except Exception as e:
                last_error = e
                error_str = str(e)
                print(f"[Agent] Gemini failed: {error_str[:200]}")
                # Don't retry on quota errors — fall through to Groq immediately

        # Fallback to Groq (try multiple models)
        if self.groq_client:
            groq_models = [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "gemma2-9b-it",
            ]
            for model in groq_models:
                try:
                    print(f"[Agent] Trying Groq {model}...")
                    response = self.groq_client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.3,
                        max_tokens=2048,
                        response_format={"type": "json_object"},
                    )
                    return response.choices[0].message.content
                except Exception as e:
                    error_str = str(e)
                    print(f"[Agent] Groq {model} failed: {error_str[:200]}")
                    last_error = e
                    if "429" not in error_str:
                        break  # Non-rate-limit error, stop trying

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    def _parse_response(self, raw: str) -> ChatResponse:
        """Parse LLM output into a validated ChatResponse."""
        # Clean the response — strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        # Parse JSON
        try:
            data = json.loads(cleaned, strict=False)
        except json.JSONDecodeError as e:
            print(f"[Agent] JSON parse error: {e}")
            print(f"[Agent] Raw response: {raw[:500]}")
            return ChatResponse(
                reply="I understand your question about SHL assessments. Could you provide more details about the role you're hiring for so I can recommend the right assessments?",
                recommendations=None,
                end_of_conversation=False,
            )

        # Extract fields with safe defaults
        reply = data.get("reply", "")
        end_of_conversation = bool(data.get("end_of_conversation", False))
        raw_recs = data.get("recommendations")

        # Validate recommendations
        recommendations = None
        if raw_recs and isinstance(raw_recs, list) and len(raw_recs) > 0:
            validated_recs = []
            for rec in raw_recs[:10]:  # Cap at 10
                if not isinstance(rec, dict):
                    continue

                name = rec.get("name", "")
                url = rec.get("url", "")
                test_type = rec.get("test_type", "K")

                # Validate URL exists in catalog
                if not url or not self.catalog.url_exists(url):
                    # Try to find by name instead
                    item = self.catalog.get_by_name(name)
                    if item:
                        url = item.link
                        test_type = item.test_type_code
                    else:
                        print(f"[Agent] Skipping invalid recommendation: {name} ({url})")
                        continue
                else:
                    # Ensure test_type matches catalog
                    item = self.catalog.get_by_url(url)
                    if item:
                        # Use agent's test_type if valid, otherwise use catalog's
                        if not test_type or test_type.strip() == "":
                            test_type = item.test_type_code

                validated_recs.append(Recommendation(
                    name=name,
                    url=url,
                    test_type=test_type,
                ))

            if validated_recs:
                recommendations = validated_recs

        return ChatResponse(
            reply=reply if reply else "How can I help you find the right SHL assessment?",
            recommendations=recommendations,
            end_of_conversation=end_of_conversation,
        )
