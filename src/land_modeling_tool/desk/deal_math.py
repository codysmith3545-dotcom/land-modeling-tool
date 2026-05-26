from __future__ import annotations

from land_modeling_tool.config import load_yaml
from land_modeling_tool.desk.types import DealMathResult
from land_modeling_tool.models.types import ControlMethod, ParcelRecord


def _desk_config() -> dict:
    return load_yaml("desk.yaml")


def _category_multiplier(category: str) -> float:
    multipliers = _desk_config().get("deal_math", {}).get("upside_multipliers", {})
    return float(multipliers.get(category, 2.0))


def compute_deal_math(parcel: ParcelRecord) -> DealMathResult:
    cfg = _desk_config().get("deal_math", {})
    category = parcel.investment_category or parcel.fit.best_category()[0]
    multiplier = _category_multiplier(category)

    basis = parcel.acquisition.basis_per_acre
    if basis <= 0 and parcel.acreage > 0:
        basis = parcel.assessed_value / parcel.acreage

    downside = parcel.acquisition.downside_value_per_acre
    if downside <= 0:
        downside = basis * 0.85

    upside = max(basis * multiplier, downside * 1.5)
    if parcel.acquisition.mispricing_signal >= 0.6:
        upside *= 1.1

    max_basis = downside + (upside - downside) * 0.35
    premium_pct = cfg.get("max_option_premium_pct_of_upside", 0.08)
    max_premium = max(upside - basis, 0) * premium_pct
    if max_premium <= 0:
        max_premium = basis * 0.05

    control = parcel.acquisition.control_method
    recommended = control.value if isinstance(control, ControlMethod) else str(control)

    spread = upside - basis
    if spread <= 0 or parcel.buy_action == "pass":
        verdict = "pass"
    elif spread / max(basis, 1) >= 2.0 and parcel.fatal.passed_all:
        verdict = "pursue"
    elif spread / max(basis, 1) >= 1.2:
        verdict = "diligence"
    else:
        verdict = "watch"

    upside_case = (
        f"{category.replace('_', ' ')} exit to {', '.join(parcel.acquisition.exit_buyers[:2]) or 'strategic buyer'} "
        f"at ~${upside:,.0f}/ac"
    )
    downside_case = f"Hold / alternate use floor ~${downside:,.0f}/ac"

    confidence = parcel.confidence.value.replace("_", " ")

    return DealMathResult(
        parcel_id=parcel.parcel_id,
        basis_per_acre=basis,
        market_value_today=basis,
        upside_per_acre=upside,
        downside_per_acre=downside,
        max_basis_per_acre=max_basis,
        max_option_premium_per_acre=max_premium,
        recommended_control=recommended,
        verdict=verdict,
        upside_case=upside_case,
        downside_case=downside_case,
        confidence=confidence,
    )


def compute_all_deal_math(parcels: list[ParcelRecord]) -> list[DealMathResult]:
    return [compute_deal_math(parcel) for parcel in parcels]
