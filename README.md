# Land Modeling Tool

Infrastructure-option land intelligence for Indiana and the Midwest. Finds controllable parcels where scarce power, water, logistics, entitlement path, and timing create option value **before** public signals price it in.

This is an **acquisition desk**, not a generic parcel search tool.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

land-model edge          # investment thesis + kill criteria
land-model inventory     # prioritized data source registry
land-model rank -n 10    # score sample parcels
land-model run           # full pipeline → outputs/
```

## What it produces

| Output | Description |
|--------|-------------|
| `outputs/infrastructure_nodes.json` | Ranked power/logistics nodes |
| `outputs/ranked_parcels.json` | Full scored parcel universe |
| `outputs/ranked_assemblages.json` | Owner/node grouped assemblages |
| `outputs/evidence_packs.json` | Source-linked thesis artifacts |
| `outputs/top_100_shortlist.json` | Serious candidates first |
| `outputs/backtest_metrics.json` | Leakage-safe precision/recall |
| `outputs/diligence_memos/*.md` | Top-10 developer-grade memos |
| `outputs/ninety_day_proof.md` | 90-day proof summary |

## Scoring model

Each parcel gets:

- **Fit scores** — data center, power-heavy industrial, logistics, manufacturing, residential, BESS/solar
- **Power readiness** — 10–50 MW, 100–300 MW, 500+ MW tiers
- **Water/wastewater fit**
- **Fatal-flaw gates** — utility, drainage, access, title, politics, exit
- **Acquisition attractiveness** — basis, mispricing, hiddenness, control method
- **Composite score + confidence band**

See [docs/PLAN.md](docs/PLAN.md) for the v2 strategy (signals, assemblages, evidence packs, temporal store).

## Configuration

- `config/investment_edge.yaml` — geography, thesis, categories, kill criteria
- `config/data_sources.yaml` — P0/P1/P2 official, paid, and signal sources
- `config/scoring_weights.yaml` — composite weights and category priority
- `config/signals.yaml` — proprietary signal types and boosts

## Sample data

`data/sample/` holds a small Indiana node/parcel/project set for local development and backtesting. Replace with live IGIO, Regrid, HIFLD, and county adapters for production.

## Architecture

```
Infrastructure nodes → parcel scoring → fatal-flaw gates → acquisition desk → backtest feedback
```

## License

Private / internal use unless otherwise specified.
