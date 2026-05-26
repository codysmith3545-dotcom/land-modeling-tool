from __future__ import annotations

from datetime import date

from land_modeling_tool.backtest.labels import build_snapshots, leakage_safe_filter, run_backtest
from land_modeling_tool.config import investment_edge, prioritized_sources
from land_modeling_tool.data.loaders import load_nodes, load_parcels, load_projects
from land_modeling_tool.models.types import DevelopmentCategory, DevelopmentEvent, GateSeverity
from land_modeling_tool.pipeline import run_pipeline
from land_modeling_tool.scoring.gates import evaluate_fatal_flaws, score_parcel
from land_modeling_tool.scoring.nodes import rank_nodes, rank_parcels


def test_investment_edge_loads():
    edge = investment_edge()
    assert edge["geography"]["primary_market"] == "Indiana"
    assert len(edge["development_categories"]) >= 5


def test_prioritized_sources_sorted():
    items = prioritized_sources()
    assert items
    priorities = [i.get("priority") for i in items]
    assert priorities.index("P0") < priorities.index("P2")


def test_rank_parcels_produces_scores():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_parcels(), nodes)
    assert parcels
    top = parcels[0]
    assert 0 <= top.composite_score <= 1
    assert top.fit.data_center >= 0


def test_fatal_flaws_block_floodway():
    parcels = load_parcels()
    bad = next(p for p in parcels if p.parcel_id == "IN-LAKE-006")
    report = evaluate_fatal_flaws(bad)
    assert "floodway_exposure" in report.blockers
    assert any(g.severity == GateSeverity.HARD for g in report.gates)
    assert any(g.severity == GateSeverity.SOFT for g in report.gates)


def test_backtest_finds_winners():
    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_parcels(), nodes)
    projects = load_projects()
    positive = {pid for e in projects for pid in e.parcel_ids}
    ranked = [p.parcel_id for p in parcels]
    metrics = run_backtest(ranked, positive)
    assert metrics.total_winners == len(positive)
    assert metrics.winners_in_top_100 >= 1


def test_leakage_safe_filter():
    event = DevelopmentEvent(
        project_id="x",
        name="x",
        category=DevelopmentCategory.DATA_CENTER,
        county="Lake",
        parcel_ids=["a"],
        first_public_signal_date=date(2021, 1, 1),
    )
    features = {"announcement": True, "county": "Lake"}
    filtered = leakage_safe_filter(features, date(2022, 1, 1), event)
    assert "announcement" not in filtered
    assert filtered["county"] == "Lake"


def test_build_snapshots():
    projects = load_projects()
    snaps = build_snapshots(projects, ["IN-CLARK-008"], as_of=date(2020, 1, 1))
    assert len(snaps) > len(projects)


def test_pipeline_runs(tmp_path):
    summary = run_pipeline(tmp_path)
    assert summary["parcels"] >= 10
    assert summary.get("assemblages", 0) >= 0
    assert summary.get("historical_projects", 0) >= 4
    assert (tmp_path / "ranked_parcels.json").exists()
    assert (tmp_path / "buy_watchlist.json").exists()
    assert (tmp_path / "development_atlas.json").exists()
    assert (tmp_path / "map.html").exists()
    assert (tmp_path / "map.geojson").exists()
    assert (tmp_path / "ranked_assemblages.json").exists()
    assert (tmp_path / "evidence_packs.json").exists()
    assert (tmp_path / "fatal_gate_detail.json").exists()
    assert (tmp_path / "ninety_day_proof.md").exists()
    assert (tmp_path / "diligence_memos").is_dir()


def test_development_atlas_builds():
    from land_modeling_tool.atlas.development_atlas import build_development_atlas

    atlas = build_development_atlas(load_parcels())
    assert atlas.project_count >= 4
    assert "data_center" in atlas.by_category
    assert atlas.winner_profiles


def test_buy_score_on_ranked_parcels():
    from land_modeling_tool.atlas.development_atlas import winner_profiles_for_scoring

    nodes = rank_nodes(load_nodes())
    profiles = winner_profiles_for_scoring(load_parcels())
    parcels = rank_parcels(load_parcels(), nodes, profiles)
    assert parcels[0].buy_score >= parcels[-1].buy_score
    assert parcels[0].buy_action in {"pursue_now", "diligence", "watch", "pass"}


def test_compute_buy_score():
    from land_modeling_tool.atlas.development_atlas import winner_profiles_for_scoring
    from land_modeling_tool.scoring.buy_score import compute_buy_score

    nodes = rank_nodes(load_nodes())
    profiles = winner_profiles_for_scoring(load_parcels())
    parcels = rank_parcels(load_parcels(), nodes, profiles)
    top = parcels[0]
    score, action = compute_buy_score(top, top.profile_match)
    assert 0 <= score <= 1
    assert action in {"pursue_now", "diligence", "watch", "pass"}


def test_assemblage_groups_same_owner():
    from land_modeling_tool.scoring.assemblage import build_assemblages

    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_parcels(), nodes)
    asm = build_assemblages(parcels)
    lake_ag = [a for a in asm if "midwest ag" in a.owner]
    assert any(a.total_acreage >= 300 for a in lake_ag)


def test_signal_boost_for_high_power_parcels():
    from land_modeling_tool.scoring.signals import detect_signals, signal_boost

    nodes = rank_nodes(load_nodes())
    parcels = rank_parcels(load_parcels(), nodes)
    lake = next(p for p in parcels if p.parcel_id == "IN-LAKE-001")
    signals = detect_signals(lake)
    assert signal_boost(lake, signals) > 0
