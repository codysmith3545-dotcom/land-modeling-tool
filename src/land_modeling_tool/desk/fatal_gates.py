from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from land_modeling_tool.models.types import (
    FatalFlawReport,
    GateResult,
    GateSeverity,
    ParcelRecord,
)


def evaluate_fatal_flaws(parcel: ParcelRecord) -> FatalFlawReport:
    gates: list[GateResult] = []
    blockers: list[str] = []
    soft_risks: list[str] = []

    jurisdiction_ok = bool(parcel.county and parcel.zoning)
    if not jurisdiction_ok:
        blockers.append("jurisdiction_missing")
    gates.append(
        GateResult("jurisdiction", jurisdiction_ok, "County and zoning identified", severity=GateSeverity.HARD)
    )

    utility_ok = parcel.power.substation_miles <= 8 and parcel.sewer_miles <= 10
    if parcel.power.substation_miles > 8:
        blockers.append("electric_service_too_distant")
    if parcel.sewer_miles > 10:
        blockers.append("sewer_extension_unlikely")
    gates.append(GateResult("utility", utility_ok, "Electric and sewer path plausible", severity=GateSeverity.HARD))

    utility_timeline_ok = parcel.power.mw_10_50 >= 0.25 and parcel.power.substation_miles <= 6
    if not utility_timeline_ok:
        blockers.append("utility_timeline_unproven")
    gates.append(
        GateResult(
            "utility_timeline",
            utility_timeline_ok,
            "Near-term utility timeline plausible from power readiness",
            severity=GateSeverity.HARD,
        )
    )

    drainage_ok = parcel.floodway_pct < 0.25 and parcel.wetland_pct < 0.40
    if parcel.floodway_pct >= 0.25:
        blockers.append("floodway_exposure")
    if parcel.wetland_pct >= 0.40:
        blockers.append("wetland_bottleneck")
    gates.append(GateResult("drainage", drainage_ok, "Drainage and wetlands reviewed", severity=GateSeverity.HARD))

    access_ok = parcel.frontage_ft >= 100
    if not access_ok:
        blockers.append("insufficient_road_frontage")
    gates.append(GateResult("access", access_ok, "Legal frontage and access plausible", severity=GateSeverity.HARD))

    env_ok = parcel.wetland_pct < 0.60
    if not env_ok:
        blockers.append("environmental_fatal_condition")
    gates.append(GateResult("environmental", env_ok, "No obvious environmental stop", severity=GateSeverity.HARD))

    title_ok = parcel.owner_count <= 12
    if not title_ok:
        blockers.append("assemblage_too_fragmented")
    gates.append(GateResult("title", title_ok, "Ownership/assemblage manageable", severity=GateSeverity.HARD))

    seller_authority_ok = parcel.owner_count <= 6
    if not seller_authority_ok:
        soft_risks.append("seller_authority_multi_owner")
    if parcel.owner_count > 16:
        blockers.append("seller_authority_unresolved")
    gates.append(
        GateResult(
            "seller_authority",
            seller_authority_ok,
            "Seller authority and signature path manageable",
            severity=GateSeverity.HARD if parcel.owner_count > 16 else GateSeverity.SOFT,
        )
    )

    marketed_pricing_ok = not parcel.listed and not parcel.industrial_park
    if not marketed_pricing_ok:
        soft_risks.append("listed_or_marketed_pricing_risk")
    gates.append(
        GateResult(
            "listed_marketed_pricing",
            marketed_pricing_ok,
            "Parcel not broadly marketed/priced",
            severity=GateSeverity.SOFT,
        )
    )

    entitlement_path = getattr(parcel.entitlement_path, "value", str(parcel.entitlement_path))
    ag_zoning = parcel.zoning.lower() in {"agricultural", "ag", "a-1"}
    rezoning_soft_ok = not (entitlement_path == "rezoning" or (ag_zoning and not parcel.flu_aligned))
    if not rezoning_soft_ok:
        soft_risks.append("rezoning_uncertainty")
    gates.append(
        GateResult(
            "rezoning_uncertainty",
            rezoning_soft_ok,
            "Entitlement path does not depend on uncertain rezoning",
            severity=GateSeverity.SOFT,
        )
    )

    if parcel.wetland_pct >= 0.05:
        soft_risks.append("wetlands_mitigation_cost")

    utility_upgrade_cost_ok = parcel.power.mw_100_300 >= 0.30 and parcel.power.substation_miles <= 5
    if not utility_upgrade_cost_ok:
        soft_risks.append("utility_upgrade_cost_risk")
    gates.append(
        GateResult(
            "utility_upgrade_cost",
            utility_upgrade_cost_ok,
            "Higher-load utility upgrade burden appears manageable",
            severity=GateSeverity.SOFT,
        )
    )

    politics_ok = not parcel.industrial_park or parcel.listed is False
    if not politics_ok:
        soft_risks.append("community_or_competitive_attention")
    gates.append(GateResult("politics", politics_ok, "Political/market posture acceptable", severity=GateSeverity.SOFT))

    exit_ok = parcel.acreage >= 20
    if not exit_ok:
        blockers.append("insufficient_scale_for_exit")
    gates.append(GateResult("exit", exit_ok, "Credible buyer/user path exists", severity=GateSeverity.HARD))

    hard_fails = sum(1 for gate in gates if gate.severity == GateSeverity.HARD and not gate.passed)
    soft_fails = sum(1 for gate in gates if gate.severity == GateSeverity.SOFT and not gate.passed)
    penalty = min(1.0, hard_fails * 0.14 + soft_fails * 0.06 + len(blockers) * 0.04)
    score = max(0.0, 1.0 - penalty)
    return FatalFlawReport(
        score=score,
        gates=gates,
        blockers=sorted(set(blockers)),
        soft_risks=sorted(set(soft_risks)),
    )


def gate_guidance(parcel: ParcelRecord, report: FatalFlawReport | None = None) -> list[str]:
    report = report or parcel.fatal
    guidance: list[str] = []

    if "electric_service_too_distant" in report.blockers or "utility_timeline_unproven" in report.blockers:
        guidance.append("Reject unless: power path verified with utility planner.")
    if "utility_upgrade_cost_risk" in report.soft_risks:
        guidance.append("Do not control until upgrade cost and timeline are bracketed.")
    if "sewer_extension_unlikely" in report.blockers:
        guidance.append("Reject unless: sewer/water extension path and cost are confirmed.")
    if "floodway_exposure" in report.blockers or "wetlands_mitigation_cost" in report.soft_risks:
        guidance.append("Reject unless: drainage outlet and wetland delineation are checked.")
    if "rezoning_uncertainty" in report.soft_risks or "fatal_zoning_prohibition" in report.blockers:
        guidance.append("Reject unless: zoning issue is checked with county staff.")
    if "insufficient_road_frontage" in report.blockers:
        guidance.append("Reject unless: legal access and frontage are confirmed on title/survey.")
    if report.blockers:
        guidance.append(f"Resolve hard blockers before spend: {', '.join(report.blockers[:3])}.")
    elif report.soft_risks:
        guidance.append("Proceed with targeted diligence on flagged soft risks only.")
    else:
        guidance.append("No soft-gate reject condition triggered.")
    return guidance


def fatal_gate_detail(parcel: ParcelRecord, report: FatalFlawReport | None = None) -> dict[str, Any]:
    report = report or parcel.fatal
    return {
        "parcel_id": parcel.parcel_id,
        "county": parcel.county,
        "passed_all": report.passed_all,
        "score": round(report.score, 3),
        "hard_fail_count": report.hard_fail_count,
        "soft_fail_count": report.soft_fail_count,
        "blockers": report.blockers,
        "soft_risks": report.soft_risks,
        "gates": [
            {
                "gate_id": gate.gate_id,
                "severity": gate.severity.value,
                "passed": gate.passed,
                "notes": gate.notes,
            }
            for gate in report.gates
        ],
        "guidance": gate_guidance(parcel, report),
    }


def build_fatal_gate_detail(parcels: list[ParcelRecord]) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parcel_count": len(parcels),
        "parcels": [fatal_gate_detail(parcel) for parcel in parcels],
    }


def gate_result_dict(report: FatalFlawReport) -> dict[str, Any]:
    return asdict(report)
