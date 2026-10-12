# Conservative entity resolution

Candidate generation joins distinct-agency advertisements of the same property type within 500 metres using indexed PostGIS `ST_DWithin`. It considers all retained advertisements, including removed ones, so historical identities are not lost. Missing coordinates cannot produce geographic candidates and reduce recall; coarse coordinates can produce candidates but cannot establish a confirmed merge.

| Feature | Default weight | Similarity |
|---|---:|---|
| Geography | .20 | `max(0, 1 - distance_m / 200)` |
| Address | .28 | Case-folded sequence similarity; zero when missing |
| Floor area | .20 | `1 - absolute difference / larger area`; zero when missing |
| Property type | .10 | Exact agreement |
| Floor | .10 | Exact known agreement |
| Rooms | .07 | Exact known agreement |
| Lift | .025 | Exact known agreement |
| Condition | .025 | Exact known agreement |

Scores are weighted and normalized by total weight. Missing values receive zero rather than inflating evidence by redistributing their weight. Default classifications are confirmed >= .90 with strong evidence, probable >= .78, uncertain >= .60, and non-match below .60. Conflicting known floors or property types are hard non-matches regardless of aggregate score.

Automatic confirmation additionally requires identical nonempty addresses, area similarity >= .95, matching known floor/rooms, different agencies, both coordinate error bounds <= 80m, and distance <= 100m. Only confirmed pairs can merge. Complete-link clustering requires every pair across two clusters to be independently confirmed; A–B and B–C alone cannot establish A–C. Ties use deterministic IDs. Cluster confidence is the minimum pair score; singleton confidence means no merge contention.

Each candidate stores IDs, distances, attribute evidence, individual feature scores, score and rule version. Decisions store classification, merge result, reason, simulated timestamp and version. Conservative cluster guards can leave a confirmed pair unmerged, with an explicit reason. Rules are configurable using JSON:

```bash
python -m app.cli deduplicate --rules docs/match-rules.example.json
```

Changing rules changes their content-addressed version. Re-running a version refreshes its last evaluated candidate evidence and decision. Persistent entities and append-only decision-event audits are production gaps.

Synthetic hard negatives include two apartments in a fictional building with matching address/coordinates, nearly equal areas and different floors. Other difficult cases have conflicting descriptions/condition, missing areas/addresses and displaced coordinates. A missing floor or uncertain coordinate prevents automatic confirmation even if other fields agree. Lowering thresholds alone does not override these strong-evidence gates.

Evaluation reads a separate private listing-to-property truth table, after resolution. True pairs include all labeled advertisements of the same underlying property, including pairs missed by candidate generation. Predicted pairs are the final clustered assignments. Precision = TP/(TP+FP), recall = TP/(TP+FN), F1 is their harmonic mean. No predictions make precision undefined (`null`); no true pairs make recall undefined. Unlabeled inventory is disclosed and is not silently evaluated.

A high precision threshold reduces wrong merges at the expense of duplicate recall. This demo intentionally prefers false negatives to false entity assignments. Performance on generated data is not evidence of production performance; a licensed, independently labeled evaluation dataset is required before deployment.
