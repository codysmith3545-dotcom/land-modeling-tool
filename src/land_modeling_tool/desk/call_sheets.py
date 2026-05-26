from __future__ import annotations

from land_modeling_tool.desk.deal_math import compute_deal_math
from land_modeling_tool.desk.thesis_matrix import build_thesis_matrix
from land_modeling_tool.models.types import ParcelRecord


def render_owner_call_sheet(parcel: ParcelRecord) -> str:
    matrix = build_thesis_matrix(parcel)
    math = compute_deal_math(parcel)
    lines = [
        f"# Owner call sheet — {parcel.parcel_id}",
        "",
        f"**Owner:** {parcel.owner or 'Unknown'}",
        f"**County:** {parcel.county} | **Acreage:** {parcel.acreage:.1f} ac",
        f"**Primary thesis:** {matrix.primary_thesis.replace('_', ' ')}",
        f"**Max basis:** ${math.max_basis_per_acre:,.0f}/ac | **Max option premium:** ${math.max_option_premium_per_acre:,.0f}/ac",
        "",
        "## Opening frame",
        "- We buy land for long-term development partnerships, not flips.",
        "- Exploring a short option while we confirm utility / entitlement path.",
        "",
        "## Questions to ask",
        "1. Would you consider a 12–18 month purchase option with modest upfront premium?",
        "2. What price expectation do you have if a qualified developer showed up?",
        "3. Any known easements, splits, mineral rights, or family disagreements on sale?",
        "4. Timeline: any life event, tax pressure, or neighbor sale influencing timing?",
        "5. Would you grant ROFR or right to match if we bring a buyer?",
        "",
        "## Do not say yet",
        "- Specific data center or hyperscaler names",
        "- Exact MW requirements or buyer identity",
        "",
        "## Must prove after call",
    ]
    for item in matrix.must_prove:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def render_utility_call_sheet(parcel: ParcelRecord) -> str:
    matrix = build_thesis_matrix(parcel)
    utility = parcel.power.utility_territory or "Unknown utility"
    lines = [
        f"# Utility call sheet — {parcel.parcel_id}",
        "",
        f"**Utility territory:** {utility}",
        f"**Nearest substation:** {parcel.power.substation_miles:.1f} mi",
        f"**Transmission:** {parcel.power.transmission_voltage_kv:.0f} kV (if known)",
        f"**Primary thesis:** {matrix.primary_thesis.replace('_', ' ')}",
        "",
        "## Questions for interconnection / planning",
        "1. Available MW at nearest substation today and in 24–36 months?",
        "2. Planned upgrades, new substation, or line reinforcements nearby?",
        "3. Typical timeline and cost range for new large load (100+ MW)?",
        "4. Queue backlog — any known constraints for this feeder?",
        "5. Who is the right contact for large-load economic development requests?",
        "",
        "## Red flags to listen for",
        "- \"No capacity until 2030+\" without upgrade plan",
        "- Requires major greenfield substation with no sponsor",
        "- Conflicting territory / co-op vs IOU boundary issues",
        "",
        "## Document after call",
        "- Contact name, date, MW available, upgrade dependency, confidence (high/med/low)",
        "",
    ]
    return "\n".join(lines)


def build_call_sheets(parcels: list[ParcelRecord]) -> dict[str, dict[str, str]]:
    sheets: dict[str, dict[str, str]] = {}
    for parcel in parcels:
        sheets[parcel.parcel_id] = {
            "owner": render_owner_call_sheet(parcel),
            "utility": render_utility_call_sheet(parcel),
        }
    return sheets
