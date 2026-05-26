from __future__ import annotations

from land_modeling_tool.config import buy_score_config
from land_modeling_tool.models.types import Hiddenness, ParcelRecord


def compute_buy_score(parcel: ParcelRecord, profile_match: float = 0.5) -> tuple[float, str]:
    cfg = buy_score_config()
    comp = cfg.get("components", {})
    hidden_map = cfg.get("hiddenness_values", {})
    penalties = cfg.get("priced_in_penalty", {})
    tiers = cfg.get("action_tiers", {})

    hidden_val = hidden_map.get(parcel.acquisition.hiddenness.value, 0.5)
    score = (
        comp.get("composite", 0.35) * parcel.composite_score
        + comp.get("acquisition", 0.25) * parcel.acquisition.attractiveness
        + comp.get("profile_match", 0.20) * profile_match
        + comp.get("hiddenness", 0.12) * hidden_val
        + comp.get("fatal", 0.08) * parcel.fatal.score
    )
    if parcel.listed:
        score *= 1.0 - penalties.get("listed", 0.25)
    if parcel.industrial_park:
        score *= 1.0 - penalties.get("industrial_park", 0.20)

    score = max(0.0, min(1.0, score))
    action = _action_tier(score, tiers)
    return score, action


def _action_tier(score: float, tiers: dict) -> str:
    if score >= tiers.get("pursue_now", 0.72):
        return "pursue_now"
    if score >= tiers.get("diligence", 0.58):
        return "diligence"
    if score >= tiers.get("watch", 0.45):
        return "watch"
    return "pass"
