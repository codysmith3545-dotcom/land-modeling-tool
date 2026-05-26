from __future__ import annotations

from datetime import date

from land_modeling_tool.backtest.labels import build_snapshots, leakage_safe_filter, run_backtest
from land_modeling_tool.config import investment_edge, prioritized_sources
from land_modeling_tool.data.loaders import load_nodes, load_parcels, load_projects
from land_modeling_tool.models.types import DevelopmentCategory, DevelopmentEvent
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
    assert (tmp_path / "ranked_parcels.json").exists()
    assert (tmp_path / "ranked_assemblages.json").exists()
    assert (tmp_path / "evidence_packs.json").exists()
    assert (tmp_path / "ninety_day_proof.md").exists()
    assert (tmp_path / "diligence_memos").is_dir()


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
