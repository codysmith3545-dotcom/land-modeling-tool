from __future__ import annotations

from land_modeling_tool.desk.fatal_gates import evaluate_fatal_flaws
from land_modeling_tool.models.types import (
    ConfidenceBand,
    ControlMethod,
    Hiddenness,
    ParcelRecord,
)
from land_modeling_tool.atlas.patterns import WinnerProfile, profile_match_score
from land_modeling_tool.config import investment_edge, scoring_weights
from land_modeling_tool.scoring.buy_score import compute_buy_score
from land_modeling_tool.scoring.parcels import entitlement_path_score, score_fit, score_power_readiness, score_water_fit
from land_modeling_tool.scoring.signals import detect_signals, signal_boost


def score_acquisition(parcel: ParcelRecord, fit_peak: float) -> None:
    basis = parcel.assessed_value / max(parcel.acreage, 1.0)
    parcel.acquisition.basis_per_acre = basis
    parcel.acquisition.downside_value_per_acre = basis * 0.85
    upside = fit_peak * 3.0
    parcel.acquisition.mispricing_signal = max(0.0, upside - (basis / 10000.0))

    hiddenness = Hiddenness.HIDDEN
    if parcel.listed or parcel.industrial_park:
        hiddenness = Hiddenness.PRICED
    elif parcel.acquisition.mispricing_signal < 0.15:
        hiddenness = Hiddenness.SEMI_OBVIOUS
    parcel.acquisition.hiddenness = hiddenness

    control = ControlMethod.OPTION
    if parcel.owner_count > 4:
        control = ControlMethod.PHASED_ASSEMBLAGE
    elif parcel.ownership_years > 20:
        control = ControlMethod.OPTION
    parcel.acquisition.control_method = control
    parcel.acquisition.owner_count = parcel.owner_count

    attractiveness = (
        0.30 * fit_peak
        + 0.25 * parcel.acquisition.mispricing_signal
        + 0.20 * (1.0 if hiddenness == Hiddenness.HIDDEN else 0.3)
        + 0.15 * (1.0 if parcel.owner_count <= 3 else 0.4)
        + 0.10 * (1.0 if parcel.fatal.passed_all else 0.0)
    )
    parcel.acquisition.attractiveness = min(1.0, attractiveness)
    parcel.acquisition.exit_buyers = _exit_buyers(parcel)


def score_parcel(
    parcel: ParcelRecord,
    node_score: float,
    winner_profiles: dict[str, WinnerProfile] | None = None,
) -> ParcelRecord:
    score_power_readiness(parcel)
    score_water_fit(parcel)
    parcel.fit = score_fit(parcel)
    parcel.fatal = evaluate_fatal_flaws(parcel)
    priority_map = _category_priority_map()
    best_cat, fit_peak = parcel.fit.investment_category(priority_map)
    parcel.investment_category = best_cat
    score_acquisition(parcel, fit_peak)

    profile = None
    if winner_profiles:
        profile = winner_profiles.get(best_cat) or winner_profiles.get("all")
    parcel.profile_match = profile_match_score(parcel, profile)

    entitlement = entitlement_path_score(parcel)
    weights = scoring_weights().get("composite", {})
    sig_boost = signal_boost(parcel)
    composite = (
        weights.get("node_score", 0.22) * node_score
        + weights.get("fit_peak", 0.28) * fit_peak
        + weights.get("power_100_300", 0.14) * parcel.power.mw_100_300
        + weights.get("water", 0.10) * parcel.water.score
        + weights.get("entitlement", 0.10) * entitlement
        + weights.get("acquisition", 0.10) * parcel.acquisition.attractiveness
        + sig_boost
        - weights.get("fatal_penalty", 0.20) * (1.0 - parcel.fatal.score)
    )
    parcel.composite_score = max(0.0, min(1.0, composite))
    parcel.buy_score, parcel.buy_action = compute_buy_score(parcel, parcel.profile_match)
    parcel.confidence = _confidence(parcel, fit_peak)
    parcel.serious_shortlist = (
        parcel.fatal.passed_all and parcel.composite_score >= 0.55 and parcel.buy_action != "pass"
    )
    signals = detect_signals(parcel)
    parcel.evidence = [
        f"Investment category: {best_cat} ({fit_peak:.2f})",
        f"Buy score: {parcel.buy_score:.2f} → {parcel.buy_action}",
        f"Winner profile match: {parcel.profile_match:.2f}",
        f"Node score: {node_score:.2f}",
        f"Power 100-300 MW readiness: {parcel.power.mw_100_300:.2f}",
        f"Water/sewer fit: {parcel.water.score:.2f}",
        f"Entitlement path: {parcel.entitlement_path.value} ({entitlement:.2f})",
        f"Signal boost: +{sig_boost:.2f}" + (f" ({', '.join(signals)})" if signals else ""),
        f"Hiddenness: {parcel.acquisition.hiddenness.value}",
        f"Control: {parcel.acquisition.control_method.value}",
    ]
    if parcel.fatal.blockers:
        parcel.evidence.append(f"Blockers: {', '.join(parcel.fatal.blockers)}")
    return parcel


def _category_priority_map() -> dict[str, float]:
    edge = investment_edge()
    multipliers = scoring_weights().get("category_priority_multiplier", {})
    out: dict[str, float] = {}
    for cat in edge.get("development_categories", []):
        pri = str(cat.get("priority", 2))
        out[cat["id"]] = float(multipliers.get(pri, 1.0))
    return out


def _confidence(parcel: ParcelRecord, fit_peak: float) -> ConfidenceBand:
    data_rich = sum(
        [
            bool(parcel.power.utility_territory),
            parcel.power.transmission_voltage_kv > 0,
            parcel.sewer_miles < 900,
            parcel.zoning != "unknown",
        ]
    )
    score = parcel.composite_score
    if score >= 0.6 and data_rich >= 3:
        return ConfidenceBand.HIGH_SCORE_HIGH_CONFIDENCE
    if score >= 0.6 or fit_peak >= 0.7:
        return ConfidenceBand.HIGH_SCORE_LOW_CONFIDENCE
    if score >= 0.4:
        return ConfidenceBand.MODERATE
    return ConfidenceBand.LOW


def _exit_buyers(parcel: ParcelRecord) -> list[str]:
    cat, _ = parcel.fit.best_category()
    mapping = {
        "data_center": ["hyperscaler", "utility"],
        "power_heavy_industrial": ["industrial_user", "utility"],
        "logistics": ["logistics_developer"],
        "manufacturing": ["industrial_user"],
        "residential_growth": ["homebuilder"],
        "bess_solar_energy": ["solar_bess_developer", "utility"],
    }
    return mapping.get(cat, ["infrastructure_fund"])
