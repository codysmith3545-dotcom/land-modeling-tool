from __future__ import annotations

from land_modeling_tool.models.types import DevelopmentEvent, InfrastructureNode, ParcelRecord


def build_ninety_day_report(
    edge: dict,
    nodes: list[InfrastructureNode],
    shortlist: list[ParcelRecord],
    metrics,
    projects: list[DevelopmentEvent],
    assemblages: list | None = None,
) -> str:
    actionable = [p for p in shortlist[:10] if p.serious_shortlist]
    lines = [
        "# 90-Day Proof Report",
        "",
        "## Thesis",
        edge["investment_thesis"]["summary"].strip(),
        "",
        "## Deliverables",
        f"- Infrastructure nodes ranked: {len(nodes)}",
        f"- Candidate parcels/assemblages: {len(shortlist)}",
        f"- Assemblage candidates: {len(assemblages or [])}",
        f"- Developer-grade diligence memos: 10",
        f"- Historical projects in backtest set: {len(projects)}",
        "",
        "## Backtest (leakage-safe sample)",
        f"- Precision@50: {metrics.precision_at_50:.2%}",
        f"- Recall@100: {metrics.recall_at_100:.2%}",
        f"- Lift over baseline: {metrics.lift_over_baseline:.2f}x",
        f"- Winners in top 100: {metrics.winners_in_top_100}/{metrics.total_winners}",
        "",
        "## Top Nodes",
    ]
    for node in nodes[:5]:
        lines.append(f"- {node.name} ({node.county}): score {node.node_score:.2f}")
    lines.extend(["", "## Actionable Shortlist (passed fatal-flaw gates)", ""])
    if actionable:
        for parcel in actionable[:10]:
            cat, fit = parcel.fit.best_category()
            lines.append(
                f"- {parcel.parcel_id} ({parcel.county}, {parcel.acreage:.0f} ac): "
                f"{cat} fit {fit:.2f}, composite {parcel.composite_score:.2f}, "
                f"hiddenness {parcel.acquisition.hiddenness.value}"
            )
    else:
        lines.append("- None passed all gates in sample set; review blockers in ranked output.")
    lines.extend(
        [
            "",
            "## Kill Criteria Check",
            f"- Actionable from first 10 memos: {len(actionable)} "
            f"(need {edge['kill_criteria']['min_actionable_from_first_10_memos']})",
            f"- Historical winners in top 100 rate: "
            f"{metrics.winners_in_top_100 / max(metrics.total_winners, 1):.0%} "
            f"(need {edge['kill_criteria']['min_historical_winners_in_top_100']:.0%})",
            "",
            "## Next Bet",
            "Double down on data center and power-heavy industrial nodes with hidden, controllable parcels.",
            "Expand proprietary signal capture: IURC dockets, county agendas, utility filings.",
            "Prioritize assemblages where one owner controls 100+ acres at a ranked node.",
        ]
    )
    return "\n".join(lines) + "\n"
