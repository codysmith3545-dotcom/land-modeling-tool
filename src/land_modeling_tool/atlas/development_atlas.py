from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

from land_modeling_tool.atlas.patterns import WinnerProfile, build_winner_profiles
from land_modeling_tool.data.loaders import load_parcels, load_projects
from land_modeling_tool.models.types import DevelopmentEvent, ParcelRecord


@dataclass
class AtlasProject:
    project_id: str
    name: str
    category: str
    county: str
    parcel_ids: list[str]
    total_acreage: float
    lat: float
    lon: float
    lead_time_months: int | None
    timeline: dict[str, str | None] = field(default_factory=dict)


@dataclass
class DevelopmentAtlas:
    """Where big development goes — retrospective layer for the master idea."""

    generated_at: str
    project_count: int
    by_category: dict[str, int]
    by_county: dict[str, int]
    projects: list[AtlasProject]
    winner_profiles: dict[str, dict]
    insights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "project_count": self.project_count,
            "by_category": self.by_category,
            "by_county": self.by_county,
            "projects": [asdict(p) for p in self.projects],
            "winner_profiles": self.winner_profiles,
            "insights": self.insights,
        }


def winner_profiles_for_scoring(parcels: list[ParcelRecord] | None = None) -> dict[str, WinnerProfile]:
    projects = load_projects()
    parcel_list = parcels or load_parcels()
    parcel_map = {p.parcel_id: p for p in parcel_list}
    category_by_parcel: dict[str, str] = {}
    winner_parcels: list[ParcelRecord] = []
    for event in projects:
        for pid in event.parcel_ids:
            category_by_parcel[pid] = event.category.value
            if pid in parcel_map:
                winner_parcels.append(parcel_map[pid])
    return build_winner_profiles(winner_parcels, category_by_parcel)


def build_development_atlas(parcels: list[ParcelRecord] | None = None) -> DevelopmentAtlas:
    projects = load_projects()
    parcel_list = parcels or load_parcels()
    parcel_map = {p.parcel_id: p for p in parcel_list}

    category_by_parcel: dict[str, str] = {}
    winner_parcels: list[ParcelRecord] = []
    atlas_projects: list[AtlasProject] = []
    by_category: dict[str, int] = {}
    by_county: dict[str, int] = {}

    for event in projects:
        cat = event.category.value
        by_category[cat] = by_category.get(cat, 0) + 1
        by_county[event.county] = by_county.get(event.county, 0) + 1

        event_parcels = [parcel_map[pid] for pid in event.parcel_ids if pid in parcel_map]
        for pid in event.parcel_ids:
            category_by_parcel[pid] = cat
        winner_parcels.extend(event_parcels)

        total_acreage = sum(p.acreage for p in event_parcels) or 0.0
        lat = sum(p.lat for p in event_parcels) / max(len(event_parcels), 1)
        lon = sum(p.lon for p in event_parcels) / max(len(event_parcels), 1)
        lead = _lead_time_months(event.land_acquisition_date, event.first_public_signal_date)

        atlas_projects.append(
            AtlasProject(
                project_id=event.project_id,
                name=event.name,
                category=cat,
                county=event.county,
                parcel_ids=event.parcel_ids,
                total_acreage=total_acreage,
                lat=lat,
                lon=lon,
                lead_time_months=lead,
                timeline={
                    "land_acquisition": _iso(event.land_acquisition_date),
                    "first_public_signal": _iso(event.first_public_signal_date),
                    "announcement": _iso(event.announcement_date),
                    "construction_start": _iso(event.construction_start_date),
                },
            )
        )

    profiles = build_winner_profiles(winner_parcels, category_by_parcel)
    insights = _generate_insights(profiles, atlas_projects)

    return DevelopmentAtlas(
        generated_at=date.today().isoformat(),
        project_count=len(projects),
        by_category=by_category,
        by_county=by_county,
        projects=atlas_projects,
        winner_profiles={k: v.to_dict() for k, v in profiles.items()},
        insights=insights,
    )


def _generate_insights(profiles: dict[str, WinnerProfile], projects: list[AtlasProject]) -> list[str]:
    insights: list[str] = []
    if "data_center" in profiles:
        m = profiles["data_center"].means
        insights.append(
            f"Data center winners avg {m.get('acreage', 0):.0f} ac, "
            f"{m.get('substation_miles', 0):.1f} mi to substation, "
            f"{m.get('transmission_voltage_kv', 0):.0f}kV."
        )
    dc_count = sum(1 for p in projects if p.category == "data_center")
    if dc_count:
        insights.append(f"{dc_count} historical data center project(s) in atlas — prioritize matching power nodes.")
    leads = [p.lead_time_months for p in projects if p.lead_time_months]
    if leads:
        avg_lead = sum(leads) / len(leads)
        insights.append(
            f"Avg lead time land control → first public signal: {avg_lead:.0f} months. "
            "Buy window is before signal, not at announcement."
        )
    insights.append(
        "Pattern: winners cluster at ranked infrastructure nodes with hidden ownership, not broker listings."
    )
    return insights


def _lead_time_months(start: date | None, signal: date | None) -> int | None:
    if not start or not signal:
        return None
    return (signal.year - start.year) * 12 + (signal.month - start.month)


def _iso(d: date | None) -> str | None:
    return d.isoformat() if d else None
