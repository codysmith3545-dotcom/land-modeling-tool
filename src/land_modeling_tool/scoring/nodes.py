from __future__ import annotations

from land_modeling_tool.atlas.patterns import WinnerProfile
from land_modeling_tool.models.types import InfrastructureNode, ParcelRecord
from land_modeling_tool.scoring.gates import score_parcel


def rank_nodes(nodes: list[InfrastructureNode]) -> list[InfrastructureNode]:
    return sorted(nodes, key=lambda n: n.node_score, reverse=True)


def rank_parcels(
    parcels: list[ParcelRecord],
    nodes: list[InfrastructureNode],
    winner_profiles: dict[str, WinnerProfile] | None = None,
) -> list[ParcelRecord]:
    node_map = {n.node_id: n.node_score for n in nodes}
    scored: list[ParcelRecord] = []
    for parcel in parcels:
        node_score = node_map.get(parcel.node_id, 0.3)
        scored.append(score_parcel(parcel, node_score, winner_profiles))
    return sorted(scored, key=lambda p: p.buy_score, reverse=True)


def top_shortlist(parcels: list[ParcelRecord], limit: int = 100) -> list[ParcelRecord]:
    serious = [p for p in parcels if p.serious_shortlist]
    by_buy = sorted(
        [p for p in parcels if not p.serious_shortlist],
        key=lambda p: p.buy_score,
        reverse=True,
    )
    ordered = serious + by_buy
    return ordered[:limit]
