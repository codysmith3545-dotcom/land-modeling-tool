from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from land_modeling_tool.config import load_yaml
from land_modeling_tool.desk.deal_math import compute_deal_math
from land_modeling_tool.desk.legal_control import LegalControlScore, compute_legal_control
from land_modeling_tool.desk.thesis_matrix import ThesisMatrix, build_thesis_matrix
from land_modeling_tool.desk.types import DealMathResult
from land_modeling_tool.models.types import ParcelRecord


@dataclass
class ControlStrategyResult:
    parcel_id: str
    recommended_control: str
    alternatives: list[str] = field(default_factory=list)
    reason: str = ""
    do_not_control: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "parcel_id": self.parcel_id,
            "recommended_control": self.recommended_control,
            "alternatives": self.alternatives,
            "reason": self.reason,
            "do_not_control": self.do_not_control,
        }


def _desk_config() -> dict[str, Any]:
    return load_yaml("desk.yaml")


def compute_control_strategy(
    parcel: ParcelRecord,
    legal_score: LegalControlScore | None = None,
    deal_math: DealMathResult | None = None,
    thesis: ThesisMatrix | None = None,
) -> ControlStrategyResult:
    cfg = _desk_config().get("control_strategy", {})
    legal_score = legal_score or compute_legal_control(parcel)
    deal_math = deal_math or compute_deal_math(parcel)
    thesis = thesis or build_thesis_matrix(parcel)

    utility_uncertainty_threshold = float(cfg.get("utility_uncertainty_threshold", 0.55))
    owner_count_phased_threshold = int(cfg.get("owner_count_phased_threshold", 3))
    outright_legal_min = float(cfg.get("outright_legal_score_min", 0.75))
    outright_utility_min = float(cfg.get("outright_utility_score_min", 0.7))
    outright_basis_buffer = float(cfg.get("outright_basis_buffer", 0.95))

    legal_cfg = _desk_config().get("legal_control", {})
    do_not_control_cutoff = float(legal_cfg.get("do_not_control_legal_score", 0.45))
    if legal_score.hard_blockers or legal_score.legal_control_score < do_not_control_cutoff:
        reason = "Hard legal blockers present; control attempts should wait for curative diligence."
        if legal_score.hard_blockers:
            reason = f"Hard blockers: {', '.join(legal_score.hard_blockers[:3])}"
        return ControlStrategyResult(
            parcel_id=parcel.parcel_id,
            recommended_control="do_not_control",
            alternatives=["watch_only", "desk_diligence_only"],
            reason=reason,
            do_not_control=True,
        )

    utility_uncertain = legal_score.utility < utility_uncertainty_threshold or max(
        parcel.power.mw_10_50,
        parcel.power.mw_100_300,
        parcel.power.mw_500_plus,
    ) < utility_uncertainty_threshold
    basis_safe_for_outright = parcel.acquisition.basis_per_acre <= (deal_math.max_basis_per_acre * outright_basis_buffer)

    recommended = "option"
    reason = "Option controls downside while preserving upside."
    alternatives = ["assignable_purchase_agreement", "phased_assemblage", "outright_purchase"]

    if parcel.owner_count >= owner_count_phased_threshold:
        recommended = "phased_assemblage"
        reason = "Multi-owner footprint benefits from staged control sequencing and holdout management."
        alternatives = ["option", "assignable_purchase_agreement"]
    elif parcel.listed and legal_score.contract.assignment_allowed:
        recommended = "assignable_purchase_agreement"
        reason = "Listed context supports fast paper control and assignment without full capital deployment."
        alternatives = ["option", "outright_purchase"]
    elif utility_uncertain and thesis.primary_thesis in {"power_led", "energy"}:
        recommended = "option"
        reason = "Utility uncertainty is still high; option structure limits risk until service is verified."
        alternatives = ["assignable_purchase_agreement", "phased_assemblage"]
    elif (
        legal_score.legal_control_score >= outright_legal_min
        and legal_score.utility >= outright_utility_min
        and deal_math.verdict in {"pursue", "diligence"}
        and basis_safe_for_outright
    ):
        recommended = "outright_purchase"
        reason = "Legal and utility confidence plus price discipline support fee-simple acquisition."
        alternatives = ["option", "assignable_purchase_agreement"]
    elif parcel.acquisition.hiddenness.value == "hidden":
        recommended = "option"
        reason = "Hidden opportunity favors quiet control with optionality and limited market signaling."
        alternatives = ["assignable_purchase_agreement", "rofr"]

    return ControlStrategyResult(
        parcel_id=parcel.parcel_id,
        recommended_control=recommended,
        alternatives=alternatives,
        reason=reason,
        do_not_control=False,
    )


def recommend_control_method(
    parcel: ParcelRecord,
    legal_score: LegalControlScore | None = None,
    deal_math: DealMathResult | None = None,
    thesis: ThesisMatrix | None = None,
) -> ControlStrategyResult:
    """Recommend how to control the land (alias for compute_control_strategy)."""
    return compute_control_strategy(parcel, legal_score, deal_math, thesis)


def compute_all_control_strategies(
    parcels: list[ParcelRecord],
    legal_scores: dict[str, LegalControlScore] | None = None,
    deal_math_map: dict[str, DealMathResult] | None = None,
    thesis_map: dict[str, ThesisMatrix] | None = None,
) -> list[ControlStrategyResult]:
    results: list[ControlStrategyResult] = []
    for parcel in parcels:
        results.append(
            compute_control_strategy(
                parcel=parcel,
                legal_score=(legal_scores or {}).get(parcel.parcel_id),
                deal_math=(deal_math_map or {}).get(parcel.parcel_id),
                thesis=(thesis_map or {}).get(parcel.parcel_id),
            )
        )
    return results
