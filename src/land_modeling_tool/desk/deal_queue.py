from __future__ import annotations

from land_modeling_tool.config import load_yaml
from land_modeling_tool.desk.legal_control import LegalControlScore
from land_modeling_tool.desk.thesis_matrix import build_thesis_matrix
from land_modeling_tool.desk.types import DealQueueItem
from land_modeling_tool.models.types import ParcelRecord


def _desk_config() -> dict:
    return load_yaml("desk.yaml")


def _next_action(
    parcel: ParcelRecord,
    primary_thesis: str,
    legal_control: LegalControlScore | None = None,
) -> tuple[str, str, str]:
    """Return (next_action, why, fastest_kill_test)."""
    if legal_control and legal_control.hard_blockers:
        blocker = legal_control.hard_blockers[0]
        return (
            "reject",
            f"Legal hard blocker: {blocker}",
            "Resolve blocker via legal diligence before any owner outreach",
        )

    if parcel.buy_action == "pass" or parcel.fatal.blockers:
        blocker = parcel.fatal.blockers[0] if parcel.fatal.blockers else "low buy score"
        return (
            "reject",
            f"Fatal flaw or pass action: {blocker}",
            "Confirm blocker is not curable within option window",
        )

    if parcel.listed and parcel.acquisition.mispricing_signal < 0.4:
        return (
            "add_comps",
            "Listed parcel with weak mispricing signal — verify comps before outreach",
            "Ask broker for recent industrial/DC land comps in county",
        )

    if primary_thesis in {"power_led", "energy"}:
        power_ready = max(
            parcel.power.mw_10_50,
            parcel.power.mw_100_300,
            parcel.power.mw_500_plus,
        )
        cfg = _desk_config().get("queue", {})
        threshold = cfg.get("power_mw_threshold_for_utility_call", 0.55)
        if power_ready < threshold or parcel.power.substation_miles > 5:
            return (
                "call_utility",
                "Power thesis but serveability unproven — utility confirmation required",
                "Ask utility: available MW at nearest substation by target date",
            )

    if not parcel.flu_aligned and parcel.zoning.lower() in {"agricultural", "ag", "a-1"}:
        return (
            "check_zoning",
            "Agricultural zoning / FLU misalignment — entitlement path unclear",
            "County planner: rezoning or PUD feasibility for primary use",
        )

    if parcel.sewer_miles > 4:
        return (
            "verify_sewer",
            f"Sewer {parcel.sewer_miles:.1f} mi away — extension cost may kill deal",
            "Utility / engineer: rough $/ft extension and capacity",
        )

    if parcel.owner_count > 2:
        return (
            "check_title",
            f"{parcel.owner_count} owners — assemblage complexity",
            "Title: easements, splits, and whether option can cover full footprint",
        )

    if parcel.buy_action in {"pursue_now", "diligence"}:
        return (
            "call_owner",
            "Gates pass and buy score supports owner conversation",
            "Owner: willing to option? timeline? price expectation vs our max basis",
        )

    return (
        "watch_only",
        "Interesting but not yet actionable — wait for signal or better basis",
        "Re-score after next catalyst (utility upgrade, rezoning, neighbor sale)",
    )


def build_deal_queue(
    parcels: list[ParcelRecord],
    limit: int = 25,
    legal_control: dict[str, LegalControlScore] | None = None,
    control_strategy: dict[str, str] | None = None,
) -> list[DealQueueItem]:
    actionable = [p for p in parcels if p.buy_action in {"pursue_now", "diligence", "watch"}]
    actionable.sort(key=lambda p: p.buy_score, reverse=True)

    items: list[DealQueueItem] = []
    for priority, parcel in enumerate(actionable[:limit], start=1):
        matrix = build_thesis_matrix(parcel)
        legal = (legal_control or {}).get(parcel.parcel_id)
        action, why, kill = _next_action(parcel, matrix.primary_thesis, legal)
        items.append(
            DealQueueItem(
                parcel_id=parcel.parcel_id,
                county=parcel.county,
                acreage=parcel.acreage,
                primary_thesis=matrix.primary_thesis,
                next_action=action,
                why=why,
                fastest_kill_test=kill,
                buy_action=parcel.buy_action,
                buy_score=parcel.buy_score,
                legal_control_score=legal.legal_control_score if legal else 0.0,
                legal_hard_blockers=list(legal.hard_blockers) if legal else [],
                recommended_control=(control_strategy or {}).get(parcel.parcel_id, ""),
                priority=priority,
            )
        )

    action_order = {a: i for i, a in enumerate(_desk_config().get("queue", {}).get("prioritize_actions", []))}

    def sort_key(item: DealQueueItem) -> tuple:
        return (action_order.get(item.next_action, 99), -item.buy_score)

    items.sort(key=sort_key)
    for idx, item in enumerate(items, start=1):
        item.priority = idx
    return items
