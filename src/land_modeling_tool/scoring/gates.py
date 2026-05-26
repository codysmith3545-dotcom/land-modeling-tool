from __future__ import annotations

from land_modeling_tool.models.types import (
    ConfidenceBand,
    ControlMethod,
    FatalFlawReport,
    GateResult,
    Hiddenness,
    ParcelRecord,
)
from land_modeling_tool.config import investment_edge, scoring_weights
from land_modeling_tool.scoring.parcels import entitlement_path_score, score_fit, score_power_readiness, score_water_fit
from land_modeling_tool.scoring.signals import detect_signals, signal_boost


def evaluate_fatal_flaws(parcel: ParcelRecord) -> FatalFlawReport:
    gates: list[GateResult] = []
    blockers: list[str] = []

    jurisdiction_ok = bool(parcel.county and parcel.zoning)
    gates.append(GateResult("jurisdiction", jurisdiction_ok, "County and zoning identified"))

    utility_ok = parcel.power.substation_miles <= 8 and parcel.sewer_miles <= 10
    if parcel.power.substation_miles > 8:
        blockers.append("electric_service_too_distant")
    if parcel.sewer_miles > 10:
        blockers.append("sewer_extension_unlikely")
    gates.append(GateResult("utility", utility_ok, "Electric and sewer path plausible"))

    drainage_ok = parcel.floodway_pct < 0.25 and parcel.wetland_pct < 0.40
    if parcel.floodway_pct >= 0.25:
        blockers.append("floodway_exposure")
    if parcel.wetland_pct >= 0.40:
        blockers.append("wetland_bottleneck")
    gates.append(GateResult("drainage", drainage_ok, "Drainage and wetlands reviewed"))

    access_ok = parcel.frontage_ft >= 100
    if not access_ok:
        blockers.append("insufficient_road_frontage")
    gates.append(GateResult("access", access_ok, "Legal frontage and access plausible"))

    env_ok = parcel.wetland_pct < 0.60
    gates.append(GateResult("environmental", env_ok, "No obvious environmental stop"))

    title_ok = parcel.owner_count <= 12
    if not title_ok:
        blockers.append("assemblage_too_fragmented")
    gates.append(GateResult("title", title_ok, "Ownership/assemblage manageable"))

    politics_ok = not parcel.industrial_park or parcel.listed is False
    gates.append(GateResult("politics", politics_ok, "Political/market posture acceptable"))

    exit_ok = parcel.acreage >= 20
    gates.append(GateResult("exit", exit_ok, "Credible buyer/user path exists"))

    penalty = min(1.0, len(blockers) * 0.18)
    score = max(0.0, 1.0 - penalty)
    return FatalFlawReport(score=score, gates=gates, blockers=blockers)


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


def score_parcel(parcel: ParcelRecord, node_score: float) -> ParcelRecord:
    score_power_readiness(parcel)
    score_water_fit(parcel)
    parcel.fit = score_fit(parcel)
    parcel.fatal = evaluate_fatal_flaws(parcel)
    priority_map = _category_priority_map()
    best_cat, fit_peak = parcel.fit.investment_category(priority_map)
    score_acquisition(parcel, fit_peak)

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
    parcel.confidence = _confidence(parcel, fit_peak)
    parcel.serious_shortlist = parcel.fatal.passed_all and parcel.composite_score >= 0.55
    signals = detect_signals(parcel)
    parcel.evidence = [
        f"Investment category: {best_cat} ({fit_peak:.2f})",
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
