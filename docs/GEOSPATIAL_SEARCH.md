# Asking-price comparable search

The endpoint accepts latitude/longitude, an initial 50m radius, a maximum radius (default 1,000m, hard limit 10,000m), minimum desired results, type, area/price ranges, condition, floor and lift. Invalid coordinate/range combinations return 422. Pagination uses `limit` and `offset`; summary counts/statistics cover all qualifying inferred properties, not only the returned page.

`ST_DWithin` operates on WGS84 geography with metre distances and GiST filtering. Radius doubles (50, 100, 200, ...) and clamps to the maximum. It stops when the minimum count is reached or the cap is reached; `minimum_met` discloses shortage. Results are restricted to active advertisements with a known positive asking price, valid area and coordinates.

Suitability requires `coordinate_accuracy_m <= min(radius / 2, 200)`. At 50m, accuracy must be <=25m. At 200m it must be <=100m. Radius expansion therefore changes both coverage and the accepted uncertainty. The sample points are displaced within declared synthetic bounds; these are demonstration error indicators, not measured provider accuracy. The center supplied by the caller is treated as a precise query point; uncertain query origins are a production extension.

Each municipality has two fictional rectangular microzones, created from the configurable `CENTERS` registry. They are **not official administrative, cadastral or market boundaries**. The origin zone is selected deterministically using `ST_Covers`; if a point lies on the seam, sorted ID precedence applies. Default searches filter coordinates against that zone's polygon. A point outside all zones yields no matches unless crossing is explicitly enabled. `allow_cross_microzone=true` permits expansion and `cross_microzone_expansion` flags returned results outside the origin zone. Administrators can replace polygons in `microzones`; seed insertion does not overwrite edits.

Results select one advertisement per inferred property, preferring more accurate coordinates, then a recent observation and stable ID. They are sorted by distance. This prevents confirmed duplicates inflating statistics, while unmerged probable duplicates remain a limitation. Responses contain radius attempts, origin/returned zones, uncertainty limit/indicators, missing fields, merge confidence, count basis, and mean/median/min/max **asking-price** statistics in EUR.

The selection favors precise coordinates, not a low or high asking price. Price comparisons must retain agency differences rather than implying a verified transaction. No result is a valuation, completed-sale price, investment recommendation or evidence that an omitted advertisement sold.

See [API examples](API_EXAMPLES.md) for captured requests and responses and the spatial/API tests for seam, radius-cap, no-zone, filter and uncertainty cases.
