from __future__ import annotations

from datetime import date

from land_modeling_tool.desk.deal_math import compute_deal_math
from land_modeling_tool.desk.deal_queue import build_deal_queue
from land_modeling_tool.desk.thesis_matrix import build_thesis_matrix
from land_modeling_tool.models.types import InfrastructureNode, ParcelRecord


def build_weekly_desk_report(
    parcels: list[ParcelRecord],
    nodes: list[InfrastructureNode] | None = None,
    as_of: date | None = None,
) -> str:
    as_of = as_of or date.today()
    queue = build_deal_queue(parcels, limit=15)
    pursue = [p for p in parcels if p.buy_action == "pursue_now"][:5]
    diligence = [p for p in parcels if p.buy_action == "diligence"][:5]

    lines = [
        f"# Weekly land desk report — {as_of.isoformat()}",
        "",
        "## Executive summary",
        f"- **Parcels scored:** {len(parcels)}",
        f"- **Pursue now:** {len([p for p in parcels if p.buy_action == 'pursue_now'])}",
        f"- **Diligence:** {len([p for p in parcels if p.buy_action == 'diligence'])}",
        f"- **Queue actions this week:** {len(queue)}",
        "",
        "## Top queue — act this week",
        "",
    ]

    if not queue:
        lines.append("_No actionable parcels in queue._")
    else:
        lines.append("| Priority | Parcel | County | Thesis | Next action | Buy score |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in queue[:10]:
            lines.append(
                f"| {item.priority} | {item.parcel_id} | {item.county} | "
                f"{item.primary_thesis} | {item.next_action} | {item.buy_score:.2f} |"
            )

    lines.extend(["", "## Pursue now (detail)", ""])
    for parcel in pursue:
        matrix = build_thesis_matrix(parcel)
        math = compute_deal_math(parcel)
        queue_item = next((i for i in queue if i.parcel_id == parcel.parcel_id), None)
        kill = queue_item.fastest_kill_test if queue_item else "Confirm utility serveability"
        lines.extend([
            f"### {parcel.parcel_id} — {parcel.county} ({parcel.acreage:.0f} ac)",
            f"- **Thesis:** {matrix.primary_thesis} (backup: {matrix.backup_thesis})",
            f"- **Why now:** {matrix.why_now}",
            f"- **Scenario bands:** downside ${math.downside_value_per_acre:,.0f}/ac | "
            f"base ${math.base_value_per_acre:,.0f}/ac | upside ${math.upside_value_per_acre:,.0f}/ac",
            f"- **Max basis:** ${math.max_basis_per_acre:,.0f}/ac | **Strike:** ${math.recommended_strike_price:,.0f}/ac | "
            f"**Recommended control:** {math.recommended_control}",
            f"- **Verdict:** {math.verdict} | **Probability:** {math.probability_bucket} | "
            f"**Capital at risk:** ${math.capital_at_risk:,.0f} | **Do not exceed:** ${math.do_not_exceed_price:,.0f}",
            f"- **Payoff band:** {math.expected_payoff_band} | **Drop-dead:** {math.drop_dead_date or 'n/a'}",
            f"- **Exercise trigger:** {math.exercise_or_assign_trigger}",
            f"- **Fastest kill test:** {kill}",
            "",
        ])

    if diligence:
        lines.extend(["## Diligence lane", ""])
        for parcel in diligence:
            matrix = build_thesis_matrix(parcel)
            lines.append(
                f"- **{parcel.parcel_id}** ({parcel.county}): {matrix.primary_thesis} — "
                f"prove: {', '.join(matrix.must_prove[:2])}"
            )
        lines.append("")

    if nodes:
        top_nodes = sorted(nodes, key=lambda n: n.node_score, reverse=True)[:3]
        lines.extend(["## Hot nodes", ""])
        for node in top_nodes:
            lines.append(f"- **{node.name}** ({node.county}): score {node.node_score:.2f}")
        lines.append("")

    lines.extend([
        "## Rejected / pass (learn)",
        "",
    ])
    passed = [p for p in parcels if p.buy_action == "pass"][:5]
    for parcel in passed:
        reason = parcel.fatal.blockers[0] if parcel.fatal.blockers else "low score"
        lines.append(f"- {parcel.parcel_id}: {reason}")
    lines.append("")

    return "\n".join(lines)
