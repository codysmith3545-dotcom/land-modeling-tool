from __future__ import annotations

from datetime import date

from land_modeling_tool.models.types import (
    BacktestMetrics,
    DevelopmentEvent,
    ParcelTimeSnapshot,
)


def build_snapshots(
    events: list[DevelopmentEvent],
    hard_negative_ids: list[str],
    as_of: date,
    horizon_months: int = 36,
) -> list[ParcelTimeSnapshot]:
    snapshots: list[ParcelTimeSnapshot] = []
    for event in events:
        cutoff = event.first_public_signal_date or event.announcement_date
        for parcel_id in event.parcel_ids:
            snapshots.append(
                ParcelTimeSnapshot(
                    parcel_id=parcel_id,
                    as_of=as_of,
                    features={"category": event.category.value, "county": event.county},
                    label_horizon_months=horizon_months,
                    developed_within_horizon=_developed_before_horizon(cutoff, as_of, horizon_months),
                    hard_negative=False,
                )
            )
    for parcel_id in hard_negative_ids:
        snapshots.append(
            ParcelTimeSnapshot(
                parcel_id=parcel_id,
                as_of=as_of,
                features={"hard_negative": True},
                label_horizon_months=horizon_months,
                developed_within_horizon=False,
                hard_negative=True,
            )
        )
    return snapshots


def _developed_before_horizon(
    signal_date: date | None, as_of: date, horizon_months: int
) -> bool:
    if signal_date is None:
        return False
    months = (signal_date.year - as_of.year) * 12 + (signal_date.month - as_of.month)
    return 0 < months <= horizon_months


def leakage_safe_filter(features: dict, as_of: date, event: DevelopmentEvent) -> dict:
    """Drop features that would not be knowable before first public signal."""
    cutoff = event.first_public_signal_date
    if cutoff is None or as_of < cutoff:
        return features
    blocked = {"announcement", "rezoning_filed", "permit_issued", "news_mention"}
    return {k: v for k, v in features.items() if k not in blocked}


def run_backtest(
    ranked_parcel_ids: list[str],
    positive_ids: set[str],
    false_positive_reasons: dict[str, int] | None = None,
) -> BacktestMetrics:
    top50 = ranked_parcel_ids[:50]
    top100 = ranked_parcel_ids[:100]
    winners_in_50 = sum(1 for pid in top50 if pid in positive_ids)
    winners_in_100 = sum(1 for pid in top100 if pid in positive_ids)
    total = len(positive_ids) or 1
    baseline = len(positive_ids) / max(len(ranked_parcel_ids), 1)
    precision_at_50 = winners_in_50 / max(len(top50), 1)
    recall_at_100 = winners_in_100 / total
    lift = (winners_in_100 / max(len(top100), 1)) / max(baseline, 0.001)
    return BacktestMetrics(
        precision_at_50=precision_at_50,
        recall_at_100=recall_at_100,
        lift_over_baseline=lift,
        winners_in_top_100=winners_in_100,
        total_winners=len(positive_ids),
        false_positive_reasons=false_positive_reasons or {},
    )
