from __future__ import annotations

from datetime import date

from land_modeling_tool.config import load_yaml
from land_modeling_tool.desk.scenario_bands import scenario_band_values
from land_modeling_tool.desk.types import DealMathResult
from land_modeling_tool.models.types import ControlMethod, ParcelRecord


def _desk_config() -> dict:
    return load_yaml("desk.yaml")


def _deal_math_config() -> dict:
    return _desk_config().get("deal_math", {})


def _category_multiplier(category: str, cfg: dict) -> float:
    multipliers = cfg.get("upside_multipliers", {})
    return float(multipliers.get(category, 2.0))


def _probability_bucket(parcel: ParcelRecord, cfg: dict) -> str:
    thresholds = cfg.get("probability_thresholds", {})
    high_cutoff = float(thresholds.get("high", 0.72))
    med_cutoff = float(thresholds.get("medium", 0.52))
    base_score = parcel.buy_score if parcel.buy_score > 0 else parcel.composite_score
    confidence_boost = {
        "high_score_high_confidence": 0.10,
        "high_score_low_confidence": -0.04,
        "moderate": 0.0,
        "low": -0.10,
    }.get(parcel.confidence.value, 0.0)
    fatal_penalty = -0.15 if not parcel.fatal.passed_all else 0.0
    blended = max(0.0, min(1.0, base_score + confidence_boost + fatal_penalty))
    if blended >= high_cutoff:
        return "high"
    if blended >= med_cutoff:
        return "med"
    return "low"


def _recommended_control(parcel: ParcelRecord, spread_ratio: float, probability_bucket: str, cfg: dict) -> str:
    control_cfg = cfg.get("control_recommendations", {})
    outright_threshold = float(control_cfg.get("outright_min_spread_ratio", 2.0))
    option_threshold = float(control_cfg.get("option_min_spread_ratio", 1.15))
    if spread_ratio >= outright_threshold and probability_bucket == "high" and parcel.fatal.passed_all:
        return ControlMethod.OUTRIGHT.value
    if spread_ratio >= option_threshold and probability_bucket in {"high", "med"}:
        return ControlMethod.OPTION.value
    if spread_ratio >= option_threshold:
        return ControlMethod.ASSIGNABLE_PSA.value
    return ControlMethod.ROFR.value


def _exercise_trigger(
    probability_bucket: str,
    base_per_acre: float,
    strike_price: float,
    hold_months: int,
    category: str,
) -> str:
    if probability_bucket == "high":
        return (
            f"Exercise if interconnect + zoning clear and buyer indications exceed "
            f"${base_per_acre:,.0f}/ac before month {max(hold_months - 3, 1)}."
        )
    if probability_bucket == "med":
        return (
            f"Assign if one credible {category.replace('_', ' ')} buyer underwrites "
            f">=${strike_price:,.0f}/ac before month {max(hold_months - 4, 1)}."
        )
    return "Keep control optionality only; terminate if no hard utility/zoning signal by drop-dead date."


def compute_deal_math(parcel: ParcelRecord) -> DealMathResult:
    cfg = _deal_math_config()
    category = parcel.investment_category or parcel.fit.best_category()[0]
    multiplier = _category_multiplier(category, cfg)

    basis = parcel.acquisition.basis_per_acre
    if basis <= 0 and parcel.acreage > 0:
        basis = parcel.assessed_value / parcel.acreage

    downside = parcel.acquisition.downside_value_per_acre
    if downside <= 0:
        downside = basis * 0.85

    upside = max(basis * multiplier, downside * 1.5)
    if parcel.acquisition.mispricing_signal >= 0.6:
        upside *= 1.1

    outright_basis_pct = float(cfg.get("outright_basis_pct_of_upside", 0.35))
    max_basis = downside + (upside - downside) * outright_basis_pct
    probability_bucket = _probability_bucket(parcel, cfg)
    premium_map = cfg.get("option_premium_pct_by_probability", {})
    premium_pct = float(premium_map.get(probability_bucket, cfg.get("max_option_premium_pct_of_upside", 0.08)))
    max_premium = max(upside - basis, 0) * premium_pct
    if max_premium <= 0:
        max_premium = basis * 0.05

    base_midpoint_pct = float(cfg.get("base_value_midpoint_pct", 0.55))
    downside_value, downside_per_acre = scenario_band_values(parcel.acreage, downside)
    base_value, base_per_acre = scenario_band_values(
        parcel.acreage,
        downside + (upside - downside) * base_midpoint_pct,
    )
    upside_value, upside_per_acre = scenario_band_values(parcel.acreage, upside)

    spread = upside - basis
    spread_ratio = spread / max(basis, 1)
    recommended = _recommended_control(parcel, spread_ratio, probability_bucket, cfg)
    strike_pct = float(cfg.get("strike_price_pct_of_max_basis", 0.95))
    recommended_strike_price = max_basis * strike_pct
    do_not_exceed_price = max_basis * parcel.acreage

    if spread <= 0 or parcel.buy_action == "pass":
        verdict = "pass"
    elif spread_ratio >= 2.0 and parcel.fatal.passed_all:
        verdict = "pursue"
    elif spread_ratio >= 1.2:
        verdict = "diligence"
    else:
        verdict = "watch"

    diligence_cfg = cfg.get("diligence_cost_per_acre", {})
    diligence_per_acre = float(diligence_cfg.get(probability_bucket, 300))
    diligence_cost_estimate = diligence_per_acre * parcel.acreage
    capital_at_risk = (max_premium + diligence_per_acre) * parcel.acreage

    hold_cfg = cfg.get("holding_period_months", {})
    holding_period_months = int(hold_cfg.get(probability_bucket, 18))
    catalyst_cfg = cfg.get("catalyst_signal_months", {})
    catalyst_months = int(catalyst_cfg.get(probability_bucket, max(holding_period_months - 3, 1)))
    current = date.today()
    month = current.month + catalyst_months
    year = current.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(current.day, 28)
    drop_dead_date = date(year, month, day).isoformat() if recommended in {
        ControlMethod.OPTION.value,
        ControlMethod.ASSIGNABLE_PSA.value,
    } else None

    expected_payoff_band = (
        f"${max(base_value - basis * parcel.acreage, 0):,.0f}–"
        f"${max(upside_value - basis * parcel.acreage, 0):,.0f} gross spread"
    )
    exercise_or_assign_trigger = _exercise_trigger(
        probability_bucket=probability_bucket,
        base_per_acre=base_per_acre,
        strike_price=recommended_strike_price,
        hold_months=holding_period_months,
        category=category,
    )

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
        downside_value=downside_value,
        downside_value_per_acre=downside_per_acre,
        base_value=base_value,
        base_value_per_acre=base_per_acre,
        upside_value=upside_value,
        upside_value_per_acre=upside_per_acre,
        recommended_strike_price=recommended_strike_price,
        expected_payoff_band=expected_payoff_band,
        capital_at_risk=capital_at_risk,
        do_not_exceed_price=do_not_exceed_price,
        probability_bucket=probability_bucket,
        holding_period_months=holding_period_months,
        diligence_cost_estimate=diligence_cost_estimate,
        drop_dead_date=drop_dead_date,
        exercise_or_assign_trigger=exercise_or_assign_trigger,
        recommended_control=recommended,
        verdict=verdict,
        upside_case=upside_case,
        downside_case=downside_case,
        confidence=confidence,
    )


def compute_all_deal_math(parcels: list[ParcelRecord]) -> list[DealMathResult]:
    return [compute_deal_math(parcel) for parcel in parcels]
