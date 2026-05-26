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
    legal_control_score: float = 0.0
    legal_hard_blockers: list[str] = field(default_factory=list)
    recommended_control: str = ""
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
            "legal_control_score": round(self.legal_control_score, 3),
            "legal_hard_blockers": self.legal_hard_blockers,
            "recommended_control": self.recommended_control,
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
    downside_value: float
    downside_value_per_acre: float
    base_value: float
    base_value_per_acre: float
    upside_value: float
    upside_value_per_acre: float
    recommended_strike_price: float
    expected_payoff_band: str
    capital_at_risk: float
    do_not_exceed_price: float
    probability_bucket: str
    holding_period_months: int
    diligence_cost_estimate: float
    drop_dead_date: str | None
    exercise_or_assign_trigger: str
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
            "downside_value": round(self.downside_value, 0),
            "downside_value_per_acre": round(self.downside_value_per_acre, 0),
            "base_value": round(self.base_value, 0),
            "base_value_per_acre": round(self.base_value_per_acre, 0),
            "upside_value": round(self.upside_value, 0),
            "upside_value_per_acre": round(self.upside_value_per_acre, 0),
            "recommended_strike_price": round(self.recommended_strike_price, 0),
            "expected_payoff_band": self.expected_payoff_band,
            "capital_at_risk": round(self.capital_at_risk, 0),
            "do_not_exceed_price": round(self.do_not_exceed_price, 0),
            "probability_bucket": self.probability_bucket,
            "holding_period_months": self.holding_period_months,
            "diligence_cost_estimate": round(self.diligence_cost_estimate, 0),
            "drop_dead_date": self.drop_dead_date,
            "exercise_or_assign_trigger": self.exercise_or_assign_trigger,
            "recommended_control": self.recommended_control,
            "verdict": self.verdict,
            "upside_case": self.upside_case,
            "downside_case": self.downside_case,
            "confidence": self.confidence,
        }
