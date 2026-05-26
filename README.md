# Land Modeling Tool

Infrastructure-option land intelligence for Indiana and the Midwest. **See where big development goes, model the land, predict the best tracts to buy** — before public signals price it in.

This is an **acquisition desk**, not a generic parcel search tool. See [docs/MASTER_IDEA.md](docs/MASTER_IDEA.md) for how the system maps to the master idea.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

land-model edge          # investment thesis + kill criteria
land-model inventory     # prioritized data source registry
land-model atlas         # where historical projects landed
land-model rank -n 10    # score sample parcels (buy_score + action)
land-model map           # GeoJSON + interactive HTML map
land-model run           # full pipeline → outputs/
```

Open `outputs/map.html` in a browser after `land-model run`.

## What it produces

| Output | Description |
|--------|-------------|
| `outputs/development_atlas.json` | Where data centers & big dev actually went |
| `outputs/buy_watchlist.json` | Pursue-now + diligence candidates |
| `outputs/map.html` | Interactive map: nodes, projects, buy actions |
| `outputs/infrastructure_nodes.json` | Ranked power/logistics nodes |
| `outputs/ranked_parcels.json` | Full scored universe (sorted by buy_score) |
| `outputs/ranked_assemblages.json` | Owner/node grouped assemblages |
| `outputs/evidence_packs.json` | Source-linked thesis artifacts |
| `outputs/top_100_shortlist.json` | Serious candidates first |
| `outputs/backtest_metrics.json` | Leakage-safe precision/recall |
| `outputs/diligence_memos/*.md` | Top-10 developer-grade memos |
| `outputs/ninety_day_proof.md` | 90-day proof summary |

## Scoring model

Each parcel gets:

- **Fit scores** — data center, power-heavy industrial, logistics, manufacturing, residential, BESS/solar
- **Winner profile match** — similarity to land that already won (development atlas)
- **Buy score + action** — `pursue_now` → `diligence` → `watch` → `pass`
- **Power readiness** — 10–50 MW, 100–300 MW, 500+ MW tiers
- **Fatal-flaw gates** — utility, drainage, access, title, politics, exit
- **Acquisition attractiveness** — basis, mispricing, hiddenness, control method

See [docs/PLAN.md](docs/PLAN.md) for the v2 strategy and [docs/MASTER_IDEA.md](docs/MASTER_IDEA.md) for the closed loop.

## Configuration

- `config/investment_edge.yaml` — geography, thesis, categories, kill criteria
- `config/data_sources.yaml` — P0/P1/P2 official, paid, and signal sources
- `config/scoring_weights.yaml` — composite weights and category priority
- `config/buy_score.yaml` — buy score weights and action tiers
- `config/signals.yaml` — proprietary signal types and boosts

## Sample data

`data/sample/` holds a small Indiana node/parcel/project set for local development and backtesting. Replace with live IGIO, Regrid, HIFLD, and county adapters for production.

## Architecture

```
Infrastructure nodes → parcel scoring → fatal-flaw gates → acquisition desk → backtest feedback
```

## License

Private / internal use unless otherwise specified.
