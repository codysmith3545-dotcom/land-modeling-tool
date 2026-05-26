# Candidate intake

Add real parcels here before statewide live data is wired up.

## CSV (`candidates.csv`)

Use the header row from the template. Required fields:

- `parcel_id` — unique ID (e.g. county parcel number or internal slug)
- `county`, `acreage`, `lat`, `lon`
- `owner`, `assessed_value`, `basis_per_acre` (optional — derived from assessed if blank)
- `utility_territory`, `substation_miles` — critical for power-led thesis
- `hiddenness` — `hidden`, `semi_obvious`, or `priced`
- `notes`, `source`, `intake_date` — audit trail

## JSON (`candidates.json`)

Optional array of objects with the same keys.

## Merge behavior

`land-model run` loads sample parcels **and** merges candidates. A candidate with the same `parcel_id` overrides the sample record.

## Schema export

```bash
land-model intake --schema
```
