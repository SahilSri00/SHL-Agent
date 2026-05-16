"""
Hybrid retrieval engine.
Combines TF-IDF text similarity with structured metadata matching
to surface the best assessment candidates for the LLM.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re

from app.catalog import Catalog, CatalogItem


# ── Category keyword triggers ────────────────────────────────────────────
# When these words appear in user messages, boost assessments from that category.
CATEGORY_TRIGGERS = {
    "Personality & Behavior": [
        "personality", "behavioral", "behaviour", "behavior", "opq",
        "workplace style", "work style", "cultural fit", "personality test",
        "interpersonal", "motivat",
    ],
    "Ability & Aptitude": [
        "cognitive", "reasoning", "aptitude", "ability", "numerical",
        "verbal", "inductive", "deductive", "verify g", "general ability",
        "problem solving", "critical thinking", "iq",
    ],
    "Simulations": [
        "simulation", "simulated", "hands-on", "practical exercise",
        "call simulation", "phone simulation",
    ],
    "Biodata & Situational Judgment": [
        "situational", "sjt", "judgement", "judgment", "scenario",
        "situational judgment",
    ],
    "Competencies": [
        "competency", "competencies", "competence",
    ],
    "Development & 360": [
        "development", "360", "feedback", "re-skill", "reskill",
        "talent audit", "coaching",
    ],
}

# ── High-frequency defaults (appear in 70%+ of traces) ──────────────────
DEFAULT_CANDIDATES = [
    "occupational personality questionnaire opq32r",  # Personality default
    "shl verify interactive g+",  # Cognitive default
]


class Retriever:
    """Hybrid retrieval: TF-IDF similarity + structured matching."""

    def __init__(self, catalog: Catalog):
        self.catalog = catalog
        self._build_index()

    def _build_index(self):
        """Build TF-IDF index over catalog items."""
        self.corpus = [item.search_text() for item in self.catalog.items]
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
            ngram_range=(1, 2),  # unigrams + bigrams for better matching
            sublinear_tf=True,
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.corpus)
        print(f"[Retriever] TF-IDF index built: {self.tfidf_matrix.shape}")

    def retrieve(
        self,
        messages: list[dict],
        top_k: int = 20,
        max_candidates: int = 25,
    ) -> list[CatalogItem]:
        """
        Retrieve the most relevant assessments for the conversation.

        Args:
            messages: Full conversation history (list of {role, content} dicts)
            top_k: Number of TF-IDF results to fetch
            max_candidates: Maximum total candidates to return

        Returns:
            Deduplicated, ranked list of CatalogItem candidates
        """
        # Extract all user messages as the query
        user_text = " ".join(
            m["content"] for m in messages if m["role"] == "user"
        )

        candidates: dict[str, tuple[CatalogItem, float]] = {}

        # ── 1. TF-IDF text similarity ──────────────────────────────────
        if user_text.strip():
            query_vec = self.vectorizer.transform([user_text])
            similarities = cosine_similarity(query_vec, self.tfidf_matrix)[0]
            top_indices = np.argsort(similarities)[-top_k:][::-1]

            for idx in top_indices:
                item = self.catalog.items[idx]
                score = float(similarities[idx])
                if score > 0.01:  # Skip near-zero matches
                    candidates[item.link] = (item, score)

        # ── 2. Category-triggered boosting ─────────────────────────────
        user_text_lower = user_text.lower()
        triggered_categories = set()
        for category, keywords in CATEGORY_TRIGGERS.items():
            for kw in keywords:
                if kw in user_text_lower:
                    triggered_categories.add(category)
                    break

        for category in triggered_categories:
            cat_items = self.catalog.get_by_category(category)
            # For non-Knowledge categories, add all (they're smaller)
            if category != "Knowledge & Skills":
                for item in cat_items:
                    if item.link not in candidates:
                        candidates[item.link] = (item, 0.3)  # Base boost score
            else:
                # For Knowledge, only add top TF-IDF matches from this category
                for item in cat_items[:15]:
                    if item.link not in candidates:
                        candidates[item.link] = (item, 0.2)

        # ── 3. Default candidates (OPQ32r, Verify G+) ─────────────────
        for default_name in DEFAULT_CANDIDATES:
            item = self.catalog.get_by_name(default_name)
            if item and item.link not in candidates:
                candidates[item.link] = (item, 0.25)

        # ── 4. Direct name matching ────────────────────────────────────
        # If user mentions a specific assessment name, include it
        for item in self.catalog.items:
            name_lower = item.name.lower()
            # Check if the assessment name (or significant part) appears in user text
            # Use word boundary matching for names with 4+ chars
            name_words = [w for w in name_lower.split() if len(w) >= 4]
            if name_words:
                # Check if all significant words appear in user text
                if all(w in user_text_lower for w in name_words[:3]):
                    if item.link not in candidates:
                        candidates[item.link] = (item, 0.5)

        # ── 5. Sort by score, deduplicate, and cap ─────────────────────
        sorted_candidates = sorted(
            candidates.values(),
            key=lambda x: x[1],
            reverse=True,
        )

        result = [item for item, score in sorted_candidates[:max_candidates]]

        print(f"[Retriever] Retrieved {len(result)} candidates "
              f"(TF-IDF + {len(triggered_categories)} triggered categories)")

        return result

    def get_items_by_names(self, names: list[str]) -> list[CatalogItem]:
        """Fetch specific assessments by name for comparison queries."""
        results = []
        for name in names:
            item = self.catalog.get_by_name(name)
            if item:
                results.append(item)
            else:
                # Fuzzy match: find closest name
                name_lower = name.lower()
                for cat_item in self.catalog.items:
                    if name_lower in cat_item.name.lower() or cat_item.name.lower() in name_lower:
                        results.append(cat_item)
                        break
        return results
