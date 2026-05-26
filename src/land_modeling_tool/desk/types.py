from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ThesisLaneScore:
    lane_id: str
    label: str
    score: float
    categories: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_id": self.lane_id,
            "label": self.label,
            "score": round(self.score, 3),
            "categories": self.categories,
        }


@dataclass
class ThesisMatrix:
    parcel_id: str
    primary_thesis: str
    backup_thesis: str
    weak_theses: list[str]
    why_now: str
    must_prove: list[str]
    lanes: list[ThesisLaneScore]

    def to_dict(self) -> dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "primary_thesis": self.primary_thesis,
            "backup_thesis": self.backup_thesis,
            "weak_theses": self.weak_theses,
            "why_now": self.why_now,
            "must_prove": self.must_prove,
            "lanes": [lane.to_dict() for lane in self.lanes],
        }


@dataclass
class DealQueueItem:
    parcel_id: str
    county: str
    acreage: float
    primary_thesis: str
    next_action: str
    why: str
    fastest_kill_test: str
    buy_action: str
    buy_score: float
    priority: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "county": self.county,
            "acreage": self.acreage,
            "primary_thesis": self.primary_thesis,
            "next_action": self.next_action,
            "why": self.why,
            "fastest_kill_test": self.fastest_kill_test,
            "buy_action": self.buy_action,
            "buy_score": round(self.buy_score, 3),
            "priority": self.priority,
        }


@dataclass
class DealMathResult:
    parcel_id: str
    basis_per_acre: float
    market_value_today: float
    upside_per_acre: float
    downside_per_acre: float
    max_basis_per_acre: float
    max_option_premium_per_acre: float
    recommended_control: str
    verdict: str
    upside_case: str
    downside_case: str
    confidence: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "basis_per_acre": round(self.basis_per_acre, 0),
            "market_value_today": round(self.market_value_today, 0),
            "upside_per_acre": round(self.upside_per_acre, 0),
            "downside_per_acre": round(self.downside_per_acre, 0),
            "max_basis_per_acre": round(self.max_basis_per_acre, 0),
            "max_option_premium_per_acre": round(self.max_option_premium_per_acre, 0),
            "recommended_control": self.recommended_control,
            "verdict": self.verdict,
            "upside_case": self.upside_case,
            "downside_case": self.downside_case,
            "confidence": self.confidence,
        }
