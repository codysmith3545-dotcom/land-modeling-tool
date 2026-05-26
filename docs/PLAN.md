# Infrastructure-Option Land Intelligence — Plan v2

Living strategy doc for the land-modeling-tool repo. This extends the original plan with execution layers that create durable edge.

## Core thesis (unchanged)

Build an **infrastructure-option desk**, not a development heat map. Wealth comes from controlling mispriced land at scarce nodes **before** power, water, entitlement, and buyer signals price it in.

## What v2 adds

### 1. Investment-category weighting

Raw fit scores are not enough. P1 categories (data center, power-heavy industrial) get priority multipliers when ranking and writing memos. A 0.88 solar fit does not beat a 0.82 data center fit when the desk is power-led.

### 2. Proprietary signal layer

Public GIS is table stakes. v2 adds a **signal registry** (`config/signals.yaml`) with typed boosts:

- IURC large-load petitions
- MISO queue POI proximity
- Substation/transmission upgrade filings
- Rezoning pre-meetings, annexation, sewer studies
- Off-market broker chatter, geotech activity

Signals apply only when knowable before `first_public_signal_date` (leakage-safe).

### 3. Assemblage engine

The best deal is often 2–12 parcels under one owner at a node. v2 groups by county + node + owner, scores total acreage and control complexity, and exports `ranked_assemblages.json`.

### 4. Evidence packs

Every top parcel gets a structured **evidence pack**: source-linked claims, signal detections, and diligence questions. This is the artifact an acquisition partner actually reads.

### 5. Temporal feature store

Parcel-time snapshots feed an in-memory store (production: Postgres/Parquet). Backtests query `as_of` dates; no feature may post-date first public signal.

## What v3 adds (master idea loop)

Closes the gap between “where development goes” and “what to buy.” See [MASTER_IDEA.md](MASTER_IDEA.md).

### 6. Development Atlas

Retrospective layer: historical projects by category, county, acreage, and timeline (land control → first signal → announcement). Outputs `development_atlas.json` and project points on the map.

### 7. Winner profiles

Learn numeric fingerprints from atlas winner parcels (acreage, power tier, hiddenness, zoning). New candidates get a **profile_match** score — “does this look like land that already won?”

### 8. Buy score + action tiers

Unified **buy_score** combines composite prediction, acquisition attractiveness, profile match, hiddenness, and fatal-flaw clearance. Action tiers: `pursue_now` → `diligence` → `watch` → `pass`. Rankings sort by buy_score, not raw fit.

### 9. Map + watchlist

`map.html` (Leaflet) layers nodes, historical projects, and candidate parcels colored by buy action. `buy_watchlist.json` is the daily acquisition queue.

## Architecture

```
Sources → Temporal Store → Node Model → Parcel + Assemblage Model
                ↓                              ↓
         Signal Intelligence            Fatal-Flaw Gates
                ↓                              ↓
         Evidence Packs  ←──────────  Acquisition Desk → Control → Feedback
```

## Scoring outputs (per parcel/assemblage)

| Output | Purpose |
|--------|---------|
| `node_score` | Quality of surrounding infrastructure node |
| `fit_scores` | Six category fits (transparent sub-models) |
| `investment_category` | Priority-weighted best category |
| `large_load_power_readiness` | 10–50 / 100–300 / 500+ MW tiers |
| `water_wastewater_fit` | Sewer path, WWTP, withdrawal/political risk |
| `entitlement_path_score` | By-right through comp-plan amendment |
| `fatal_flaw_score` | Eight gates + explicit blockers |
| `acquisition_attractiveness` | Basis, hiddenness, control, exit buyers |
| `signal_boost` | Proprietary pre-market signals |
| `profile_match` | Similarity to historical winner parcels |
| `buy_score` | Action-oriented acquisition score |
| `buy_action` | pursue_now / diligence / watch / pass |
| `mispricing_signal` | Upside vs current basis |
| `confidence_band` | High/low confidence separation |
| `evidence_pack` | Source-linked thesis artifact |

## 90-day proof (unchanged bar, richer outputs)

1. Node map + ranked assemblages
2. 100–200 candidate parcels
3. 10 diligence memos + evidence packs
4. Leakage-safe backtest (precision@50, recall@100)
5. Kill criteria review

## Kill criteria

- ≥3 actionable tracts from first 10 memos
- ≤70% utility-expert rejection on power-led sites
- ≥20% historical winners in top 100 pre-signal
- Pivot if >50% of shortlist is already marketed/priced

## Phase roadmap

### Phase A — Now (this repo)

Sample data pipeline, transparent scoring, assemblages, signals stub, backtest scaffold.

### Phase B — Indiana live

- IGIO parcel boundaries + annual snapshots
- HIFLD transmission/substations + IURC territories
- County zoning adapters (Lake, Hamilton, Hendricks, Clark, Fayette first)
- 30–75 labeled historical projects 2018–2026

### Phase C — Moat

- Meeting-minutes pipeline (county, utility, sewer, plan commission)
- IURC/MISO watcher with alert → signal boost
- Land-control database (who optioned before announcement)
- Expert rejection tracking on top 10 memos

### Phase D — Midwest expansion

Ohio, Michigan, Illinois, Kentucky with same node → parcel → assemblage stack.

## First wedge (default)

- **Geography:** Indiana statewide
- **Priority:** Data center + power-heavy industrial nodes
- **Minimum tiers:** 20+ ac general, 100+ ac campus, 300+ ac hyperscale
- **Control:** Options and phased assemblage before outright buys

## Sources

- [IGIO Parcel Boundaries Current](https://gisdata.in.gov/server/rest/services/Hosted/Parcel_Boundaries_of_Indiana_Current/FeatureServer)
- [AES Indiana Data Centers](https://www.aesindiana.com/data-centers)
- [IEDC Data Center Tax Exemption](https://iedc.in.gov/indiana-advantages/investments/data-center-sales-tax-exemption/overview)
