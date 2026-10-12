# Captured API examples

These are actual HTTP 200 responses from the local Docker/PostGIS demonstration after the accelerated **14-day simulation**. The timestamps refer to synthetic observations, not pilot operation. Decimal advertisement prices serialize as strings; summary statistics are numeric EUR. UUIDs are deterministic for the default seed, but property anchors can change with resolution.

## GET /health

```bash
curl 'http://localhost:8089/health'
```

```json
{
  "status": "ok",
  "synthetic": true,
  "postgis": "3.5 USE_GEOS=1 USE_PROJ=1 USE_STATS=1",
  "migration": "a7186a141f72"
}
```

## GET /api/v1/properties?municipality=Bari&limit=2

```bash
curl 'http://localhost:8089/api/v1/properties?municipality=Bari&limit=2'
```

```json
{
  "synthetic": true,
  "total": 142,
  "limit": 2,
  "offset": 0,
  "items": [
    {
      "id": "036a13a3-2563-5bce-9f9e-b46a66959124",
      "synthetic": true,
      "transaction_status": "unknown",
      "deduplication_confidence": 1.0,
      "listing_count": 1,
      "representative_listing": {
        "id": "aa0521fe-4cb5-5944-9738-fdd7b76addb3",
        "property_id": "036a13a3-2563-5bce-9f9e-b46a66959124",
        "source_id": "synthetic-network",
        "agency_id": "fictional-agency-4",
        "original_source_id": " AD-00760 ",
        "url": "https://fictional-agency-4.invalid/synthetic/AD-00760",
        "municipality": "Bari",
        "address": "SYNTHETIC block 095, unit 0",
        "description": "SYNTHETIC property; no correspondence to a real listing.",
        "property_type": "apartment",
        "asking_price_eur": "416000.00",
        "area_sqm": 175.0,
        "rooms": 6,
        "floor": 4,
        "condition": "good",
        "lift": false,
        "latitude": 41.120865049642944,
        "longitude": 16.87592836903724,
        "coordinate_accuracy_m": 8.0,
        "coordinate_provenance": "synthetic_exact",
        "availability": "active",
        "published_at": "2026-01-01T09:00:00Z",
        "first_seen_at": "2026-01-01T09:00:00Z",
        "last_seen_at": "2026-01-14T09:00:00Z",
        "state_updated_at": "2026-01-14T09:00:00Z",
        "synthetic": true,
        "missing_attributes": [],
        "attributes": {
          "garden": false,
          "balcony": false,
          "parking": false,
          "storage": true,
          "terrace": false,
          "bathrooms": 2,
          "energy_class": null,
          "building_year": 1955,
          "building_units": 17
        }
      }
    },
    {
      "id": "05b5a45a-87da-56d5-972e-44cef10070a0",
      "synthetic": true,
      "transaction_status": "unknown",
      "deduplication_confidence": 1.0,
      "listing_count": 1,
      "representative_listing": {
        "id": "12e441e8-d97a-5d09-8f30-31f461326067",
        "property_id": "05b5a45a-87da-56d5-972e-44cef10070a0",
        "source_id": "synthetic-network",
        "agency_id": "fictional-agency-4",
        "original_source_id": " AD-00712 ",
        "url": "https://fictional-agency-4.invalid/synthetic/AD-00712",
        "municipality": "Bari",
        "address": "SYNTHETIC block 089, unit 0",
        "description": "SYNTHETIC property; no correspondence to a real listing.",
        "property_type": "apartment",
        "asking_price_eur": "460000.00",
        "area_sqm": 171.0,
        "rooms": 6,
        "floor": 1,
        "condition": "needs_renovation",
        "lift": false,
        "latitude": 41.11854820084098,
        "longitude": 16.8741743098252,
        "coordinate_accuracy_m": 8.0,
        "coordinate_provenance": "synthetic_exact",
        "availability": "active",
        "published_at": "2025-12-20T09:00:00Z",
        "first_seen_at": "2026-01-01T09:00:00Z",
        "last_seen_at": "2026-01-14T09:00:00Z",
        "state_updated_at": "2026-01-14T09:00:00Z",
        "synthetic": true,
        "missing_attributes": [],
        "attributes": {
          "garden": false,
          "balcony": true,
          "parking": false,
          "storage": false,
          "terrace": false,
          "bathrooms": 2,
          "energy_class": "E",
          "building_year": 1969,
          "building_units": 9
        }
      }
    }
  ]
}
```

## GET /api/v1/properties/036a13a3-2563-5bce-9f9e-b46a66959124

```bash
curl 'http://localhost:8089/api/v1/properties/036a13a3-2563-5bce-9f9e-b46a66959124'
```

```json
{
  "id": "036a13a3-2563-5bce-9f9e-b46a66959124",
  "synthetic": true,
  "transaction_status": "unknown",
  "deduplication_confidence": 1.0,
  "listings": [
    {
      "id": "aa0521fe-4cb5-5944-9738-fdd7b76addb3",
      "property_id": "036a13a3-2563-5bce-9f9e-b46a66959124",
      "source_id": "synthetic-network",
      "agency_id": "fictional-agency-4",
      "original_source_id": " AD-00760 ",
      "url": "https://fictional-agency-4.invalid/synthetic/AD-00760",
      "municipality": "Bari",
      "address": "SYNTHETIC block 095, unit 0",
      "description": "SYNTHETIC property; no correspondence to a real listing.",
      "property_type": "apartment",
      "asking_price_eur": "416000.00",
      "area_sqm": 175.0,
      "rooms": 6,
      "floor": 4,
      "condition": "good",
      "lift": false,
      "latitude": 41.120865049642944,
      "longitude": 16.87592836903724,
      "coordinate_accuracy_m": 8.0,
      "coordinate_provenance": "synthetic_exact",
      "availability": "active",
      "published_at": "2026-01-01T09:00:00Z",
      "first_seen_at": "2026-01-01T09:00:00Z",
      "last_seen_at": "2026-01-14T09:00:00Z",
      "state_updated_at": "2026-01-14T09:00:00Z",
      "synthetic": true,
      "missing_attributes": [],
      "attributes": {
        "garden": false,
        "balcony": false,
        "parking": false,
        "storage": true,
        "terrace": false,
        "bathrooms": 2,
        "energy_class": null,
        "building_year": 1955,
        "building_units": 17
      }
    }
  ]
}
```

## GET /api/v1/listings/aa0521fe-4cb5-5944-9738-fdd7b76addb3/history

```bash
curl 'http://localhost:8089/api/v1/listings/aa0521fe-4cb5-5944-9738-fdd7b76addb3/history'
```

```json
{
  "listing_id": "aa0521fe-4cb5-5944-9738-fdd7b76addb3",
  "synthetic": true,
  "transaction_status": "unknown",
  "total_observations": 14,
  "total_price_events": 1,
  "limit": 50,
  "offset": 0,
  "observations": [
    {
      "observed_at": "2026-01-01T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-02T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-03T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-04T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-05T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-06T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-07T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-08T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-09T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-10T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-11T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-12T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-13T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    },
    {
      "observed_at": "2026-01-14T09:00:00Z",
      "availability": "active",
      "asking_price_eur": "416000.00",
      "inferred": false
    }
  ],
  "asking_price_history": [
    {
      "observed_at": "2026-01-01T09:00:00Z",
      "previous_price_eur": null,
      "asking_price_eur": "416000.00",
      "event_type": "initial"
    }
  ]
}
```

## GET /api/v1/comparables?latitude=41.1171&longitude=16.8719&limit=2

```bash
curl 'http://localhost:8089/api/v1/comparables?latitude=41.1171&longitude=16.8719&limit=2'
```

```json
{
  "synthetic": true,
  "search_radius_used_m": 200.0,
  "attempted_radii_m": [
    50.0,
    100.0,
    200.0
  ],
  "origin_microzone": "Bari:east",
  "cross_microzone_allowed": false,
  "cross_microzone_expansion": false,
  "coordinate_accuracy_limit_m": 100.0,
  "comparable_listing_count": 8,
  "count_basis": "one advertisement per deduplicated property",
  "minimum_met": true,
  "asking_price_statistics_eur": {
    "count": 8,
    "mean": 195187.5,
    "median": 167100.0,
    "min": 117000.0,
    "max": 383000.0
  },
  "items": [
    {
      "id": "d68d27fc-610c-57fb-b4ba-c67407ef0088",
      "property_id": "c2332ba6-e2ed-5c6c-b9e1-3b1f54022a21",
      "source_id": "synthetic-network",
      "agency_id": "fictional-agency-4",
      "original_source_id": " AD-00736 ",
      "url": "https://fictional-agency-4.invalid/synthetic/AD-00736",
      "municipality": "Bari",
      "address": "SYNTHETIC block 092, unit 0",
      "description": "SYNTHETIC property; no correspondence to a real listing.",
      "property_type": "apartment",
      "asking_price_eur": "117000.00",
      "area_sqm": 70.0,
      "rooms": 2,
      "floor": 2,
      "condition": "renovated",
      "lift": false,
      "latitude": 41.11722447983942,
      "longitude": 16.871927472067757,
      "coordinate_accuracy_m": 8.0,
      "coordinate_provenance": "synthetic_exact",
      "availability": "active",
      "published_at": "2025-12-16T09:00:00Z",
      "first_seen_at": "2026-01-01T09:00:00Z",
      "last_seen_at": "2026-01-14T09:00:00Z",
      "state_updated_at": "2026-01-14T09:00:00Z",
      "synthetic": true,
      "missing_attributes": [],
      "attributes": {
        "garden": false,
        "balcony": false,
        "parking": false,
        "storage": false,
        "terrace": false,
        "bathrooms": 1,
        "energy_class": "F",
        "building_year": 1984,
        "building_units": 19
      },
      "distance_m": 14.02,
      "microzone_id": "Bari:east",
      "deduplication_confidence": 1.0,
      "coordinate_accuracy_indicator": "precise",
      "transaction_status": "unknown"
    },
    {
      "id": "d688a969-2302-5ff8-b719-b88ab35d703a",
      "property_id": "84505f20-e6b3-56fc-9a3e-8e2e2b83fab2",
      "source_id": "synthetic-network",
      "agency_id": "fictional-agency-3",
      "original_source_id": " AD-01320 ",
      "url": "https://fictional-agency-3.invalid/synthetic/AD-01320",
      "municipality": "Bari",
      "address": "SYNTHETIC block 040, unit 0",
      "description": "SYNTHETIC alternative agency description; may conflict.",
      "property_type": "apartment",
      "asking_price_eur": "184300.00",
      "area_sqm": 90.0,
      "rooms": 3,
      "floor": 1,
      "condition": "good",
      "lift": false,
      "latitude": 41.11723096715248,
      "longitude": 16.87195805935852,
      "coordinate_accuracy_m": 20.0,
      "coordinate_provenance": "synthetic_exact",
      "availability": "active",
      "published_at": "2026-01-01T09:00:00Z",
      "first_seen_at": "2026-01-01T09:00:00Z",
      "last_seen_at": "2026-01-14T09:00:00Z",
      "state_updated_at": "2026-01-14T09:00:00Z",
      "synthetic": true,
      "missing_attributes": [],
      "attributes": {
        "garden": false,
        "balcony": false,
        "parking": false,
        "storage": false,
        "terrace": false,
        "bathrooms": 1,
        "energy_class": "F",
        "building_year": 1952,
        "building_units": 20
      },
      "distance_m": 15.34,
      "microzone_id": "Bari:east",
      "deduplication_confidence": 0.983916,
      "coordinate_accuracy_indicator": "precise",
      "transaction_status": "unknown"
    }
  ],
  "limit": 2,
  "offset": 0,
  "data_limitations": [
    "All records and microzone boundaries are synthetic demonstration data.",
    "Statistics describe asking prices, not completed sales or verified market values.",
    "Coordinate accuracy is a declared synthetic error bound, not a measured geocode guarantee.",
    "Conservative deduplication may leave probable duplicates counted separately."
  ]
}
```

## GET /api/v1/quality/summary

```bash
curl 'http://localhost:8089/api/v1/quality/summary'
```

```json
{
  "synthetic": true,
  "validation_label": "14-day simulation; not a continuously operated pilot",
  "as_of": "2026-01-14T09:00:00Z",
  "simulation_days": 14,
  "total_raw_listings": 21380,
  "distinct_source_advertisements": 1600,
  "unique_deduplicated_properties": 1162,
  "active_advertisements": 1540,
  "removed_advertisements": 60,
  "price_change_events": 661,
  "missing_field_percentages": {
    "asking_price_eur": 2.0625,
    "area_sqm": 1.875,
    "address": 3.375,
    "rooms": 0.0,
    "floor": 0.0,
    "condition": 0.0,
    "lift": 0.0,
    "bathrooms": 3.1875,
    "energy_class": 6.4375,
    "building_year": 0.0,
    "balcony": 0.0,
    "terrace": 0.0,
    "parking": 0.0,
    "storage": 0.0,
    "garden": 0.0
  },
  "coordinate_accuracy_distribution": {
    "approximate_21_200m": 166,
    "coarse_over_200m": 144,
    "precise_0_20m": 1290
  },
  "deduplication": {
    "synthetic": true,
    "evaluation": "pairwise final clusters; all truth pairs, including blocked candidates",
    "labeled_listings": 1600,
    "unlabeled_listings": 0,
    "true_positives": 438,
    "false_positives": 0,
    "false_negatives": 162,
    "precision": 1.0,
    "recall": 0.73,
    "f1": 0.8439306358381503
  },
  "ingestion": {
    "processing_runs": 14,
    "successful_runs": 14,
    "partial_runs": 0,
    "failed_runs": 0,
    "success_rate": 1.0
  },
  "data_freshness": {
    "stale_active_listings": 0,
    "stale_threshold_days": 3,
    "max_active_age_days": 0.0,
    "basis": "latest simulated observation time, not wall-clock operation"
  },
  "costs": {
    "simulated": true,
    "currency": "EUR",
    "provider_charges": 4.276,
    "processing_charges": 0.21,
    "infrastructure_charges": 10.5,
    "total_operational_cost": 14.986,
    "usable_listings": 1350,
    "usable_deduplicated_count": 971,
    "cost_per_1000_usable": 15.433574,
    "denominator": "active deduplicated properties with at least one usable advertisement",
    "usable_criteria": {
      "price_required": true,
      "positive_area_required": true,
      "coordinates_required": true,
      "max_accuracy_m": 200.0
    },
    "rates": {
      "provider_eur_per_raw_record": 0.0002,
      "processing_eur_per_run": 0.015,
      "infrastructure_eur_per_simulated_day": 0.75
    }
  },
  "alerts": [
    {
      "check": "deduplication_recall",
      "value": 0.73,
      "threshold": 0.75
    }
  ],
  "data_limitations": [
    "All records and microzone boundaries are synthetic demonstration data.",
    "Statistics describe asking prices, not completed sales or verified market values.",
    "Coordinate accuracy is a declared synthetic error bound, not a measured geocode guarantee.",
    "Conservative deduplication may leave probable duplicates counted separately.",
    "Availability changes are not transaction evidence; transaction statuses are unknown.",
    "Cost rates are illustrative assumptions, not invoices or quoted provider prices."
  ],
  "raw_count_basis": "input rows across runs, including quarantine; replays excluded",
  "temporarily_unavailable_advertisements": 0,
  "validation": {
    "quarantined_records": 0,
    "invalid_area_records": 0,
    "duplicate_source_identifiers": 0,
    "schema_changes": 0,
    "invalid_coordinate_records": 0
  },
  "source_coverage": {
    "Bari": 200,
    "Bitonto": 200,
    "Conversano": 200,
    "Giovinazzo": 200,
    "Modugno": 200,
    "Mola di Bari": 200,
    "Noicattaro": 200,
    "Triggiano": 200
  }
}
```

## GET /api/v1/ingestion/runs?limit=2

```bash
curl 'http://localhost:8089/api/v1/ingestion/runs?limit=2'
```

```json
{
  "synthetic": true,
  "total": 14,
  "limit": 2,
  "offset": 0,
  "items": [
    {
      "id": "bdaad800-1b60-5931-bda4-6f9fc4842166",
      "source_id": "synthetic-network",
      "observed_at": "2026-01-14T09:00:00Z",
      "started_at": "2026-10-11T18:44:13.735911Z",
      "finished_at": "2026-10-11T18:44:19.901191Z",
      "complete": true,
      "scope": [
        "Bari",
        "Modugno",
        "Bitonto",
        "Triggiano",
        "Mola di Bari",
        "Giovinazzo",
        "Noicattaro",
        "Conversano"
      ],
      "status": "success",
      "stats": {
        "accepted": 1540,
        "quarantined": 0,
        "raw_records": 1540,
        "observations": 1540,
        "out_of_order": 0,
        "price_changes": 49,
        "schema_changes": 0,
        "inferred_removals": 0,
        "duplicate_source_identifiers": 0
      },
      "synthetic": true
    },
    {
      "id": "2a62cb94-f3c4-55dd-abf6-7343a3e21c2b",
      "source_id": "synthetic-network",
      "observed_at": "2026-01-13T09:00:00Z",
      "started_at": "2026-10-11T18:44:07.952457Z",
      "finished_at": "2026-10-11T18:44:13.195741Z",
      "complete": true,
      "scope": [
        "Bari",
        "Modugno",
        "Bitonto",
        "Triggiano",
        "Mola di Bari",
        "Giovinazzo",
        "Noicattaro",
        "Conversano"
      ],
      "status": "success",
      "stats": {
        "accepted": 1540,
        "quarantined": 0,
        "raw_records": 1540,
        "observations": 1540,
        "out_of_order": 0,
        "price_changes": 49,
        "schema_changes": 0,
        "inferred_removals": 0,
        "duplicate_source_identifiers": 0
      },
      "synthetic": true
    }
  ]
}
```

## GET /api/v1/deduplication/metrics

```bash
curl 'http://localhost:8089/api/v1/deduplication/metrics'
```

```json
{
  "synthetic": true,
  "evaluation": "pairwise final clusters; all truth pairs, including blocked candidates",
  "labeled_listings": 1600,
  "unlabeled_listings": 0,
  "true_positives": 438,
  "false_positives": 0,
  "false_negatives": 162,
  "precision": 1.0,
  "recall": 0.73,
  "f1": 0.8439306358381503
}
```
