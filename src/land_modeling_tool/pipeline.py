from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from land_modeling_tool.atlas.development_atlas import build_development_atlas, winner_profiles_for_scoring
from land_modeling_tool.backtest.labels import build_snapshots, run_backtest
from land_modeling_tool.config import OUTPUT_DIR, investment_edge, prioritized_sources
from land_modeling_tool.data.candidate_intake import load_all_parcels
from land_modeling_tool.data.loaders import load_hard_negatives, load_nodes, load_projects
from land_modeling_tool.desk.call_sheets import build_call_sheets
from land_modeling_tool.desk.control_strategy import compute_all_control_strategies
from land_modeling_tool.desk.deal_math import compute_all_deal_math
from land_modeling_tool.desk.deal_queue import build_deal_queue
from land_modeling_tool.desk.fatal_gates import build_fatal_gate_detail
from land_modeling_tool.desk.feedback import rejection_summary
from land_modeling_tool.desk.legal_control import compute_all_legal_control
from land_modeling_tool.desk.thesis_matrix import build_all_thesis_matrices
from land_modeling_tool.desk.weekly_report import build_weekly_desk_report
from land_modeling_tool.export.geojson import build_geojson, write_geojson
from land_modeling_tool.export.map_html import write_interactive_map
from land_modeling_tool.proof.diligence_memo import render_memo
from land_modeling_tool.proof.ninety_day import build_ninety_day_report
from land_modeling_tool.scoring.assemblage import build_assemblages
from land_modeling_tool.scoring.evidence import build_evidence_pack
from land_modeling_tool.scoring.gates import _category_priority_map
from land_modeling_tool.scoring.nodes import rank_nodes, rank_parcels, top_shortlist
from land_modeling_tool.scoring.signals import detect_signals
from land_modeling_tool.temporal.store import TemporalFeatureStore


def run_pipeline(output_dir: Path | None = None) -> dict:
    out = output_dir or OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    edge = investment_edge()
    raw_parcels = load_all_parcels()
    atlas = build_development_atlas(raw_parcels)
    profiles = winner_profiles_for_scoring(raw_parcels)

    nodes = rank_nodes(load_nodes())
    node_map = {n.node_id: n for n in nodes}
    parcels = rank_parcels(raw_parcels, nodes, profiles)
    assemblages = build_assemblages(parcels)
    shortlist = top_shortlist(parcels, limit=100)
    buy_now = [p for p in parcels if p.buy_action in {"pursue_now", "diligence"}][:25]

    projects = load_projects()
    hard_negatives = load_hard_negatives()

    positive_ids = {pid for event in projects for pid in event.parcel_ids}
    ranked_ids = [p.parcel_id for p in parcels]
    fp_reasons: dict[str, int] = {}
    for parcel in parcels:
        if parcel.parcel_id not in positive_ids and parcel.composite_score >= 0.55:
            for blocker in parcel.fatal.blockers:
                fp_reasons[blocker] = fp_reasons.get(blocker, 0) + 1

    metrics = run_backtest(ranked_ids, positive_ids, fp_reasons)
    snapshots = build_snapshots(projects, hard_negatives, as_of=date(2020, 1, 1))
    store = TemporalFeatureStore()
    store.from_snapshots(snapshots)

    priority_map = _category_priority_map()
    evidence_packs = []
    for parcel in shortlist[:25]:
        node = node_map.get(parcel.node_id)
        pack = build_evidence_pack(parcel, node, detect_signals(parcel))
        evidence_packs.append(pack.to_dict())

    geojson = build_geojson(parcels, nodes, atlas)

    _write_json(out / "investment_edge.json", edge)
    _write_json(out / "data_source_inventory.json", prioritized_sources())
    _write_json(out / "development_atlas.json", atlas.to_dict())
    _write_json(out / "infrastructure_nodes.json", [asdict(n) for n in nodes])
    _write_json(out / "ranked_parcels.json", [_parcel_dict(p, priority_map) for p in parcels])
    _write_json(out / "buy_watchlist.json", [_parcel_dict(p, priority_map) for p in buy_now])
    _write_json(out / "ranked_assemblages.json", [asdict(a) for a in assemblages])
    _write_json(out / "top_100_shortlist.json", [_parcel_dict(p, priority_map) for p in shortlist])
    _write_json(out / "evidence_packs.json", evidence_packs)
    _write_json(out / "fatal_gate_detail.json", build_fatal_gate_detail(parcels))
    _write_json(out / "backtest_metrics.json", asdict(metrics))
    _write_json(out / "parcel_time_snapshots.json", [asdict(s) for s in snapshots])
    _write_json(out / "temporal_feature_store.json", [asdict(f) for f in store.features])
    write_geojson(out / "map.geojson", geojson)
    write_interactive_map(out / "map.html", geojson)

    (out / "development_atlas_report.md").write_text(
        _atlas_markdown(atlas),
        encoding="utf-8",
    )

    report_path = out / "ninety_day_proof.md"
    report_path.write_text(
        build_ninety_day_report(edge, nodes, shortlist, metrics, projects, assemblages),
        encoding="utf-8",
    )

    thesis = build_all_thesis_matrices(parcels)
    thesis_map = {t.parcel_id: t for t in thesis}
    deal_math = compute_all_deal_math(parcels)
    deal_math_map = {d.parcel_id: d for d in deal_math}
    legal_control = compute_all_legal_control(parcels)
    legal_control_map = {l.parcel_id: l for l in legal_control}
    control_strategy = compute_all_control_strategies(
        parcels,
        legal_scores=legal_control_map,
        deal_math_map=deal_math_map,
        thesis_map=thesis_map,
    )
    control_strategy_map = {c.parcel_id: c.recommended_control for c in control_strategy}
    queue = build_deal_queue(
        parcels,
        legal_control=legal_control_map,
        control_strategy=control_strategy_map,
    )
    call_sheets = build_call_sheets([p for p in parcels if p.parcel_id in {q.parcel_id for q in queue[:10]}])

    _write_json(out / "parcel_thesis_matrix.json", [m.to_dict() for m in thesis])
    _write_json(out / "deal_queue.json", [q.to_dict() for q in queue])
    _write_json(out / "deal_math.json", [d.to_dict() for d in deal_math])
    _write_json(out / "legal_control.json", [l.to_dict() for l in legal_control])
    _write_json(out / "control_strategy.json", [c.to_dict() for c in control_strategy])
    _write_json(out / "expert_rejection_summary.json", rejection_summary())

    memos_dir = out / "diligence_memos"
    memos_dir.mkdir(exist_ok=True)
    memo_ids = {item.parcel_id for item in queue[:10]}
    memo_parcels = [p for p in parcels if p.parcel_id in memo_ids]
    if not memo_parcels:
        memo_parcels = shortlist[:10]
    for parcel in memo_parcels:
        memo_path = memos_dir / f"{parcel.parcel_id}.md"
        memo_path.write_text(render_memo(parcel), encoding="utf-8")

    sheets_dir = out / "call_sheets"
    sheets_dir.mkdir(exist_ok=True)
    for parcel_id, sheets in call_sheets.items():
        (sheets_dir / f"{parcel_id}_owner.md").write_text(sheets["owner"], encoding="utf-8")
        (sheets_dir / f"{parcel_id}_utility.md").write_text(sheets["utility"], encoding="utf-8")

    (out / "weekly_desk_report.md").write_text(
        build_weekly_desk_report(parcels, nodes),
        encoding="utf-8",
    )

    return {
        "output_dir": str(out),
        "nodes": len(nodes),
        "parcels": len(parcels),
        "candidates_merged": len(raw_parcels),
        "assemblages": len(assemblages),
        "shortlist": len(shortlist),
        "buy_watchlist": len(buy_now),
        "deal_queue": len(queue),
        "historical_projects": atlas.project_count,
        "precision_at_50": metrics.precision_at_50,
        "recall_at_100": metrics.recall_at_100,
        "map": str(out / "map.html"),
        "weekly_desk_report": str(out / "weekly_desk_report.md"),
    }


def _atlas_markdown(atlas) -> str:
    lines = [
        "# Development Atlas",
        "",
        f"Historical projects tracked: **{atlas.project_count}**",
        "",
        "## By category",
    ]
    for cat, count in sorted(atlas.by_category.items()):
        lines.append(f"- {cat}: {count}")
    lines.extend(["", "## By county"])
    for county, count in sorted(atlas.by_county.items()):
        lines.append(f"- {county}: {count}")
    lines.extend(["", "## Projects", ""])
    for p in atlas.projects:
        lines.append(
            f"- **{p.name}** ({p.category}, {p.county}) — {p.total_acreage:.0f} ac, "
            f"lead time {p.lead_time_months or '?'} mo"
        )
    lines.extend(["", "## Insights", ""])
    for insight in atlas.insights:
        lines.append(f"- {insight}")
    return "\n".join(lines) + "\n"


def _parcel_dict(parcel, priority_map: dict[str, float] | None = None) -> dict:
    data = asdict(parcel)
    priority_map = priority_map or _category_priority_map()
    data["best_category"] = parcel.investment_category or parcel.fit.investment_category(priority_map)[0]
    data["best_fit_score"] = parcel.fit.investment_category(priority_map)[1]
    data["raw_best_category"], data["raw_best_fit_score"] = parcel.fit.best_category()
    return data


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
