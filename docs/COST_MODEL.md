# Simulated operating-cost model

All costs are illustrative EUR assumptions. The repository has no paid provider calls and these numbers are **not measured actual expenses, cloud bills, provider quotations or proof of commercial unit economics**.

For each distinct ingested snapshot, `source_costs` records provider charges on raw records and a fixed processing charge. Exact snapshot replays create neither runs nor charges. Infrastructure charges are calculated from the inclusive span of simulated observation dates.

| Assumption | Default EUR | Configuration |
|---|---:|---|
| Per raw source record | .0002 | SIMULATED_PROVIDER_PER_RECORD_EUR |
| Per processing run | .015 | SIMULATED_PROCESSING_PER_RUN_EUR |
| Per simulated infrastructure day | .75 | SIMULATED_INFRASTRUCTURE_PER_DAY_EUR |

```text
provider = sum(raw_records_in_distinct_runs * provider_rate)
processing = distinct_processing_runs * processing_rate
infrastructure = simulated_days * infrastructure_daily_rate
total_operational_cost = provider + processing + infrastructure
cost_per_1000_usable = total_operational_cost / usable_deduplicated_count * 1000
```

A usable advertisement must be active, have a known positive asking price/area, have coordinates, and have declared accuracy <= the configurable `MAX_USABLE_ACCURACY_M`. The denominator counts distinct inferred entities having at least one usable advertisement. The report separately exposes usable advertisements and usable deduplicated count. An empty denominator returns `null` rather than dividing by zero.

Raw input rows include quarantined records and repeated advertisements on different days; distinct source listings, inferred properties, active advertisements and usable entities are separate measures. Duplicate recall affects this cost denominator: missed duplicates inflate it and make the unit cost look lower, a disclosed modeling limitation.

Included: illustrative acquisition, processing and base infrastructure. Excluded: VAT, licensing negotiations, human review, paid geocoding, production observability/backups, traffic, engineering effort, support and commercial margins. A production estimate must use measured throughput, source contracts, retention/backup needs, billing regions and verified invoices. The demo does not benchmark CPU or claim production operating-cost savings.
