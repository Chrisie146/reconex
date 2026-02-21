"""
Bank Plugin Registry - Central registration and discovery system for bank parsers.

Each bank is a self-contained plugin that registers:
  - Detection config (PDF keywords, CSV scoring logic)
  - CSV adapter (BankAdapter subclass)
  - Optional PDF parser function

Adding a new bank = adding one file in bank_plugins/ that calls registry.register().
No changes needed in bank_detector.py, bank_adapters.py, or pdf_parser.py.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from services.bank_adapters import BankAdapter


@dataclass
class BankPluginConfig:
    """Declarative configuration for a bank plugin."""

    # Identity
    bank_id: str  # e.g. "nedbank" – must match BankType enum value
    bank_name: str  # Human-readable, e.g. "Nedbank"

    # PDF detection keywords (case-insensitive substrings matched against OCR/text)
    pdf_keywords: List[str] = field(default_factory=list)

    # CSV header patterns used by the generic scorer (regex, case-insensitive)
    csv_header_patterns: Dict[str, List[str]] = field(default_factory=dict)

    # Expected date formats (strptime strings)
    date_formats: List[str] = field(default_factory=list)

    # Date regex for sample-row scoring
    date_regex: str = ""


class BankPlugin(ABC):
    """Base class for all bank plugins.

    Subclasses MUST set ``config`` and implement ``get_adapter()``.
    Optionally override ``score_csv()`` for custom scoring and
    ``parse_pdf()`` for PDF-specific extraction.
    """

    config: BankPluginConfig

    # ------------------------------------------------------------------
    # CSV detection
    # ------------------------------------------------------------------

    def score_csv(
        self,
        headers_str: str,
        headers: List[str],
        sample_rows: Optional[List[List[str]]] = None,
    ) -> float:
        """Score how likely a CSV belongs to this bank (0.0 – 1.0).

        Default implementation uses ``config.csv_header_patterns`` and
        ``config.date_regex``.  Override for bank-specific logic.
        """
        score = 0.0
        patterns = self.config.csv_header_patterns

        for _canonical, regexes in patterns.items():
            for pat in regexes:
                if re.search(pat, headers_str, re.IGNORECASE):
                    score += 0.2
                    break

        # Date format bonus from sample rows
        if sample_rows and self.config.date_regex:
            for row in sample_rows[:3]:
                for cell in row:
                    if re.match(self.config.date_regex, str(cell).strip()):
                        score += 0.15
                        break
                if score >= 0.9:
                    break

        return min(score, 1.0)

    # ------------------------------------------------------------------
    # PDF detection
    # ------------------------------------------------------------------

    def matches_pdf_text(self, text_lower: str) -> bool:
        """Return True if the extracted/OCR text matches this bank's keywords."""
        return any(kw in text_lower for kw in self.config.pdf_keywords)

    # ------------------------------------------------------------------
    # Adapter factory
    # ------------------------------------------------------------------

    @abstractmethod
    def get_adapter(self) -> "BankAdapter":
        """Return a BankAdapter instance for CSV normalisation."""
        ...

    # ------------------------------------------------------------------
    # Optional PDF parser
    # ------------------------------------------------------------------

    def parse_pdf(
        self,
        text: str,
        pdf_obj: Any = None,
        statement_year: Optional[int] = None,
    ) -> Optional[List[List[str]]]:
        """Bank-specific PDF/OCR text → list of [date, description, amount] rows.

        Return ``None`` to indicate this plugin has no PDF parser (fall back to
        generic extraction).
        """
        return None


# ======================================================================
# Singleton registry
# ======================================================================


class BankRegistry:
    """Global registry of bank plugins."""

    _plugins: Dict[str, BankPlugin] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    @classmethod
    def register(cls, plugin: BankPlugin) -> None:
        bank_id = plugin.config.bank_id
        cls._plugins[bank_id] = plugin

    @classmethod
    def get_plugin(cls, bank_id: str) -> Optional[BankPlugin]:
        return cls._plugins.get(bank_id)

    @classmethod
    def all_plugins(cls) -> Dict[str, BankPlugin]:
        return dict(cls._plugins)

    # ------------------------------------------------------------------
    # CSV detection (replaces BankDetector.detect)
    # ------------------------------------------------------------------

    @classmethod
    def detect_from_csv(
        cls,
        headers: List[str],
        sample_rows: Optional[List[List[str]]] = None,
    ) -> Tuple[str, float]:
        """Score all registered plugins and return (bank_id, confidence).

        Returns ("unknown", 0.0) when no plugin scores above 0.3.
        """
        headers_str = " ".join(h.lower() for h in headers)

        best_id = "unknown"
        best_score = 0.0

        for bank_id, plugin in cls._plugins.items():
            if bank_id in ("unknown", "generic"):
                continue
            score = plugin.score_csv(headers_str, headers, sample_rows)
            if score > best_score:
                best_score = score
                best_id = bank_id

        if best_score < 0.3:
            return "unknown", best_score

        return best_id, best_score

    # ------------------------------------------------------------------
    # PDF detection (replaces keyword if/elif chain in pdf_parser.py)
    # ------------------------------------------------------------------

    @classmethod
    def detect_from_pdf_text(cls, text: str) -> Optional[str]:
        """Detect bank from extracted/OCR text.  Returns bank_id or None."""
        text_lower = text.lower()
        for bank_id, plugin in cls._plugins.items():
            if bank_id in ("unknown", "generic"):
                continue
            if plugin.matches_pdf_text(text_lower):
                return bank_id
        return None

    # ------------------------------------------------------------------
    # Adapter lookup (replaces get_adapter factory)
    # ------------------------------------------------------------------

    @classmethod
    def get_adapter(cls, bank_id: str) -> "BankAdapter":
        plugin = cls._plugins.get(bank_id)
        if plugin:
            return plugin.get_adapter()

        # Fallback to generic
        generic = cls._plugins.get("generic") or cls._plugins.get("unknown")
        if generic:
            return generic.get_adapter()

        # Last resort – import directly
        from services.bank_adapters import GenericAdapter
        return GenericAdapter()

    # ------------------------------------------------------------------
    # PDF parser lookup
    # ------------------------------------------------------------------

    @classmethod
    def get_pdf_parser(cls, bank_id: str) -> Optional[Callable]:
        plugin = cls._plugins.get(bank_id)
        if plugin and plugin.parse_pdf.__func__ is not BankPlugin.parse_pdf:
            return plugin.parse_pdf
        return None

    # ------------------------------------------------------------------
    # Info helpers
    # ------------------------------------------------------------------

    @classmethod
    def list_banks(cls) -> List[Dict[str, str]]:
        """Return list of registered banks for UI display."""
        return [
            {"bank_id": bid, "bank_name": p.config.bank_name}
            for bid, p in cls._plugins.items()
            if bid not in ("unknown", "generic")
        ]

    @classmethod
    def get_bank_name(cls, bank_id: str) -> str:
        plugin = cls._plugins.get(bank_id)
        return plugin.config.bank_name if plugin else "Unknown"
