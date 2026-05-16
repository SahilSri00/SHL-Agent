"""
Catalog data layer.
Loads the SHL product catalog JSON and provides lookup/search utilities.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional


# ── Test-type letter code mapping ────────────────────────────────────────────
KEY_TO_CODE = {
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Ability & Aptitude": "A",
    "Biodata & Situational Judgment": "B",
    "Simulations": "S",
    "Competencies": "C",
    "Development & 360": "D",
    "Assessment Exercises": "E",
}


@dataclass
class CatalogItem:
    """Structured representation of an SHL assessment."""
    entity_id: str
    name: str
    link: str
    job_levels: list[str]
    languages: list[str]
    duration: str
    remote: str
    adaptive: str
    description: str
    keys: list[str]  # e.g., ["Knowledge & Skills", "Simulations"]
    test_type_code: str = ""  # e.g., "K,S"

    def __post_init__(self):
        codes = []
        for k in self.keys:
            code = KEY_TO_CODE.get(k)
            if code:
                codes.append(code)
        self.test_type_code = ",".join(codes) if codes else "K"

    def compact_repr(self) -> str:
        """Compact text for LLM prompt — kept short to minimize tokens."""
        dur = self.duration if self.duration else "—"
        desc = self.description[:150] + "..." if len(self.description) > 150 else self.description
        return (
            f"{self.name} | Type: {self.test_type_code} | "
            f"Duration: {dur} | "
            f"Levels: {', '.join(self.job_levels[:3]) if self.job_levels else 'General'}\n"
            f"  {desc}"
        )

    def search_text(self) -> str:
        """Text blob used for TF-IDF indexing."""
        return (
            f"{self.name} {self.name} "  # double-weight the name
            f"{self.description} "
            f"{' '.join(self.keys)} "
            f"{' '.join(self.job_levels)} "
            f"{' '.join(self.languages)}"
        )


class Catalog:
    """In-memory SHL assessment catalog."""

    def __init__(self, catalog_path: Optional[str] = None):
        if catalog_path is None:
            catalog_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "shl_product_catalog.json"
            )
        self.items: list[CatalogItem] = []
        self._by_url: dict[str, CatalogItem] = {}
        self._by_name_lower: dict[str, CatalogItem] = {}
        self._load(catalog_path)

    def _load(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            raw = f.read()
        data = json.loads(raw, strict=False)

        for entry in data:
            item = CatalogItem(
                entity_id=entry.get("entity_id", ""),
                name=entry.get("name", ""),
                link=entry.get("link", ""),
                job_levels=entry.get("job_levels", []),
                languages=entry.get("languages", []),
                duration=entry.get("duration", ""),
                remote=entry.get("remote", ""),
                adaptive=entry.get("adaptive", ""),
                description=entry.get("description", ""),
                keys=entry.get("keys", []),
            )
            self.items.append(item)
            self._by_url[item.link.rstrip("/")] = item
            self._by_name_lower[item.name.lower()] = item

        print(f"[Catalog] Loaded {len(self.items)} assessments")

    def get_by_url(self, url: str) -> Optional[CatalogItem]:
        return self._by_url.get(url.rstrip("/"))

    def get_by_name(self, name: str) -> Optional[CatalogItem]:
        return self._by_name_lower.get(name.lower())

    def url_exists(self, url: str) -> bool:
        return url.rstrip("/") in self._by_url

    def get_by_category(self, category: str) -> list[CatalogItem]:
        return [item for item in self.items if category in item.keys]

    def get_all_urls(self) -> set[str]:
        return set(self._by_url.keys())
