# Reproducibility summary, 2026-09-28

Every figure quoted in a shipped project's README and findings memo, re-measured on a fresh pull of its sources by the project's own notebook. Same bytes must give the same number; different bytes are publisher drift and are read under the contract in `ci/policy.yml`.

| Project | Listed | Reproduced | Drift | Outside band | Failed | Not run | Not reproducible | Sources | Report |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 01: Seller Risk Scoring | 56 | 56 | 0 | 0 | 0 | 0 | 0 | olist_kaggle unchanged | [2026-09-28](01-seller-risk/2026-09-28.md) |
| 02: Funnel and Retention | 22 | 22 | 0 | 0 | 0 | 0 | 0 | cosmetics_kaggle unchanged | [2026-09-28](02-funnel-retention/2026-09-28.md) |
| 03: Defence Procurement Intelligence | 337 | 143 | 168 | 23 | 0 | 0 | 3 | canadabuys_history changed | [2026-09-28](03-defence-procurement/2026-09-28.md) |
| 04: Wind Repowering Uplift | 220 | 209 | 4 | 0 | 2 | 0 | 5 | uswtdb_current unchanged; uswtdb_2018_archive unchanged; eia923_closed unchanged; eia923_provisional changed | [2026-09-28](04-wind-repowering/2026-09-28.md) |
| 06: Ontario Demand Forecast | 284 | 277 | 6 | 0 | 0 | 0 | 1 | ieso_demand_closed unchanged; ieso_demand_current changed; ieso_zonal_closed unchanged; ieso_zonal_current changed | [2026-09-28](06-ontario-demand-forecast/2026-09-28.md) |
| 05-additive-trade | excluded | | | | | | | In build in a parallel session and not yet committed. Its backfill is eight StatCan CIMT packages, about 3.1 GB of zips over 1988 to 2026, which does not fit a scheduled runner. To be revisited when it ships; a cached Parquet artifact keyed on its run log is the likely route.
 | |

Badge: 707 of 919 on 2026-09-28, 201 drifted, 2 failed (red).

**04: Wind Repowering Uplift failed.** 2 figure(s) differ on unchanged source bytes.
