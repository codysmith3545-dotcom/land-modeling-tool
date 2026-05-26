from __future__ import annotations

from land_modeling_tool.desk.types import ThesisLaneScore, ThesisMatrix
from land_modeling_tool.models.types import Hiddenness, ParcelRecord


def _lane_scores(parcel: ParcelRecord) -> list[ThesisLaneScore]:
    fit = parcel.fit
    power_led = max(fit.data_center, fit.power_heavy_industrial)
    logistics = max(fit.logistics, fit.manufacturing)
    energy = fit.bess_solar_energy

    optionality = 0.35 * fit.best_category()[1]
    if parcel.acquisition.hiddenness == Hiddenness.HIDDEN:
        optionality += 0.25
    if parcel.acquisition.mispricing_signal >= 0.55:
        optionality += 0.15
    if len(parcel.acquisition.exit_buyers) >= 2:
        optionality += 0.1
    optionality = min(optionality, 1.0)

    return [
        ThesisLaneScore(
            lane_id="power_led",
            label="Power-led",
            score=power_led,
            categories=["data_center", "power_heavy_industrial"],
        ),
        ThesisLaneScore(
            lane_id="logistics_industrial",
            label="Logistics / industrial",
            score=logistics,
            categories=["logistics", "manufacturing"],
        ),
        ThesisLaneScore(
            lane_id="energy",
            label="Energy",
            score=energy,
            categories=["bess_solar_energy"],
        ),
        ThesisLaneScore(
            lane_id="cheap_optionality",
            label="Cheap optionality",
            score=optionality,
            categories=["multi_exit"],
        ),
    ]


def _must_prove(parcel: ParcelRecord, primary: str) -> list[str]:
    proofs: list[str] = []
    if primary in {"power_led", "energy"}:
        if parcel.power.mw_100_300 < 0.5:
            proofs.append("Serveable MW by target date (not just proximity)")
        if not parcel.power.utility_territory:
            proofs.append("Utility territory and interconnection path")
    if parcel.sewer_miles > 3:
        proofs.append("Sewer extension feasibility and cost")
    if not parcel.flu_aligned:
        proofs.append("Future land use / comp plan alignment")
    if parcel.floodway_pct > 0 or parcel.wetland_pct > 5:
        proofs.append("Wetland / floodway mitigation path")
    if parcel.listed:
        proofs.append("Seller is not already pricing in the thesis")
    if parcel.owner_count > 1:
        proofs.append("Assemblage control path across owners")
    if not proofs:
        proofs.append("Title, access, and basis vs exit buyers")
    return proofs[:5]


def _why_now(parcel: ParcelRecord, primary: str) -> str:
    if parcel.listed:
        return "Listed — verify whether thesis is already priced in before outreach."
    if primary == "power_led" and parcel.power.mw_100_300 >= 0.5:
        return "Power serveability signal present — confirm MW before seller/market wakes up."
    if parcel.acquisition.hiddenness == Hiddenness.HIDDEN:
        return "Still off-market / under-radar relative to node demand."
    if parcel.buy_action == "pursue_now":
        return "Buy score and gates support near-term pursuit."
    return "Score supports diligence; confirm catalyst timing before control spend."


def build_thesis_matrix(parcel: ParcelRecord) -> ThesisMatrix:
    lanes = _lane_scores(parcel)
    ranked = sorted(lanes, key=lambda lane: lane.score, reverse=True)
    primary = ranked[0].lane_id
    backup = ranked[1].lane_id if len(ranked) > 1 else ranked[0].lane_id
    weak = [lane.lane_id for lane in ranked if lane.score < 0.45]

    return ThesisMatrix(
        parcel_id=parcel.parcel_id,
        primary_thesis=primary,
        backup_thesis=backup,
        weak_theses=weak,
        why_now=_why_now(parcel, primary),
        must_prove=_must_prove(parcel, primary),
        lanes=lanes,
    )


def build_all_thesis_matrices(parcels: list[ParcelRecord]) -> list[ThesisMatrix]:
    return [build_thesis_matrix(parcel) for parcel in parcels]
