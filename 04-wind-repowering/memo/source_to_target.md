# Source to target

Every column the analysis reads, where it came from, what was done to it on the way, and
the check that guards it. Raw headers are quoted exactly as the source spells them. Where a
transform is "as text", the raw table keeps the source's own spelling and the cast happens
in the target column named on the same row, so a value that fails the cast is visible
rather than guessed.

The three raw tables are loaded with every column as text. That is deliberate: both
publishers use sentinels (`-9999`, `missing`, `.`) that a type guess would either turn into
a number or drop, and I want to count them before anything is cast.

## Turbines, current release (`raw_turbines_current` to `fct_turbine`, `dim_plant`)

Source: USGS US Wind Turbine Database, PostgREST API, one row per turbine. 75,727 rows and
28 columns on the 2026-09-03 pull. The manifest with the hash is `memo/pull_manifest.json`.

| Raw header | Target | Transform | Guarding check |
|---|---|---|---|
| `case_id` | `fct_turbine.case_id` | as text, the turbine key | B1: no duplicates (0 found) |
| `eia_id` | `fct_turbine.plant_id`, `dim_plant.plant_id` | `TRY_CAST` to integer; blank and null both mean no plant | B2: 3,615 turbines (4.8%) carry none and never reach the generation data |
| `usgs_pr_id` | `fct_turbine.usgs_pr_id` | as text; the bridge to the 2018 file | D-06: bridges 92.2% of retrofitted turbines; 13 project ids span two plants and are excluded from the bridge |
| `p_name` | `fct_turbine.p_name` | as text | none; not used as a key (measured worse than the project id, D-06) |
| `p_year` | `fct_turbine.p_year`, `dim_plant.first_p_year` (minimum over the plant) | `TRY_CAST` to integer | B3: 1.5% null. B5: equals the retrofit year on 1,529 retrofitted turbines across 17 plants, so it is a repowering year, not a build year, on those rows |
| `t_state`, `t_county` | `fct_turbine.t_state`, `t_county`; `dim_plant.t_state` (any value over the plant) | as text | none |
| `t_manu`, `t_model` | `fct_turbine.t_manu`, `t_model` | as text | none; not used in the estimate. This is the closest the source comes to describing the machine and it says nothing about blade material |
| `t_cap` | `fct_turbine.t_cap_kw`; `dim_plant.total_cap_mw` (sum over the plant, divided by 1,000) | `TRY_CAST` to double | B3: 4.3% null; plant capacity sums are understated where any turbine is null |
| `t_hh`, `t_rd`, `t_rsa` | `fct_turbine.t_hh_m`, `t_rd_m`, `t_rsa_m2`; `plant_rotor.rotor_m_today` (mean of `t_rd` over the plant) | `TRY_CAST` to double | B3: `t_rd` 4.7% null |
| `t_retrofit` | `fct_turbine.retrofitted`; `dim_plant.n_retrofitted` (count of `'1'` over the plant) | `= '1'` to boolean | B4: no retrofitted turbine lacks a retrofit year (0 found) |
| `t_retro_yr` | `fct_turbine.retrofit_year`; `dim_plant.cohort_year` (minimum over the plant's retrofitted turbines); `dim_plant.n_retrofit_years` | `TRY_CAST` to integer | B7: no treated plant spreads retrofits over more than one year (0 found) |
| `xlong`, `ylat` | `fct_turbine.longitude`, `latitude` | `TRY_CAST` to double | none; used only by the dashboard map |
| `faa_ors`, `faa_asn`, `t_fips`, `p_tnum`, `p_cap`, `t_ttlh`, `t_conf_atr`, `t_conf_loc`, `t_img_date`, `t_img_src`, `t_offshore` | not carried | loaded as text in the raw table, not staged | none; not read by anything downstream |

Derived on `dim_plant` and `plant_scope`, with no raw header of their own:

| Target | Built from | Rule | Guarding check |
|---|---|---|---|
| `plant_scope.status` | `n_retrofitted`, `n_turbines` | `treated` where every turbine was retrofitted, `control` where none, `mixed` otherwise | B6: 29 mixed plants set aside (D-02) |
| `plant_scope.build_year_rewritten` | B5 rows | true where any retrofitted turbine at the plant has `p_year` equal to its retrofit year | 13 treated plants; excluded from setting the vintage window |
| `plant_scope.vintage_lo`, `vintage_hi` | `first_p_year` of treated plants not rewritten | the window a control must fall inside | measured 2001 to 2012 (D-04) |
| `plant_scope.control_eligible` | `status`, `first_p_year`, window | control inside the window | 567 of 1,208 controls |

## Turbines, April 2018 release (`raw_turbines_2018` to `plant_cap_2018`, `plant_rotor`)

Source: the earliest archived release of the same database, `uswtdb_v1_0_20180419.zip`.
57,636 rows and 24 columns. It has no `eia_id`, so it can only reach a plant through the
project id and the current file, and it is used for the pre-repowering baselines only.

| Raw header | Target | Transform | Guarding check |
|---|---|---|---|
| `usgs_pr_id` | join key to the bridge built from the current file | as text | bridge restricted to project ids that map to exactly one plant today |
| `t_cap` | `plant_cap_2018.cap_mw_2018` (sum over the project, divided by 1,000) | `-9999` excluded explicitly, then `TRY_CAST` to double | 3,041 sentinel rows in the file; `capacity_missing` counts them per plant and is 0 on every study plant |
| `t_rd` | `plant_rotor.rotor_m_2018` (mean over the project) | `-9999` excluded explicitly, then `TRY_CAST` to double | 5,137 sentinel rows in the file; `rotor_missing_2018` counts them per plant |
| `case_id` | not used | | D-06: only 10.5% of retrofitted turbines keep their id across releases, 0% for four cohorts, so it is not a key here |
| `p_year` | not used | | 113 sentinel rows; the vintage window is set from the current file |

Derived: `plant_rotor.rotor_change_pct` is `100 * (rotor_m_today - rotor_m_2018) / rotor_m_2018`,
and a plant is `rotor grew` above +2%, `rotor unchanged or smaller` at or below it. B15: 4 of the
80 treated plants in the study have no rotor record on both sides and are `unknown`.

## Generation (`EIA-923` sheets to `fct_generation_plant_year`)

Source: EIA-923, one archive per year 2013 to 2025, workbook `EIA923_Schedules_2_3_4_5_*.xlsx`
matched on the schedule numbers because the rest of the name changes, sheet
`Page 1 Generation and Fuel Data`, header on row index 5, 97 columns in every year. Rows
are kept where `Reported Fuel Type Code` is `WND`, which gives 14,203 rows across the range.

| Raw header | Target | Transform | Guarding check |
|---|---|---|---|
| `Plant Id` | `plant_id` | `to_numeric` with coercion, then integer | 0 non-numeric rows |
| `YEAR` | `year` | `to_numeric` with coercion, then integer | 19 rows carry `.` and go to `dq_generation_quarantine` rather than being dropped |
| `Plant State` (2013 spells it `State`) | `plant_state` | rename map, first value per plant-year | B8: the required list is checked on every year after the map; a missing column stops the load and names the year |
| `Net Generation (Megawatthours)` | `net_gen_mwh` (sum over the plant-year) | `to_numeric` with coercion, summed | 0 mismatches above 1 MWh against the sum of the twelve monthly columns; B9 counts plant-years at or below zero; B12: 11 plant-years built from more than one wind row |
| `Netgen January` to `Netgen December` (2013 spells them `Netgen_Jan` to `Netgen_Dec`) | reconciliation only | rename map, summed and compared to the annual column | see above |
| `Reported Fuel Type Code` | filter | `= 'WND'` | none |
| `source_file` | `source_file` | the workbook name inside the archive | one workbook per year, checked before load |
| everything else on the sheet | not carried | fuel consumption and heat content for other technologies | none |

Derived on `panel` and `panel_balanced`:

| Target | Rule | Guarding check |
|---|---|---|
| `panel.log_gen` | `LN(net_gen_mwh)` where positive, else null | non-positive rows survive in the table and are counted, not dropped |
| `panel.rel_time` | `year - cohort_year` on treated plants | |
| `panel.post` | 1 on a treated plant from its cohort year on | |
| `panel_balanced` | plants with all twelve years 2013 to 2024 present and positive | B10: 53 of 639 plants fail the balance test and are the unbalanced-panel sensitivity (D-05) |
| 2025 | in `fct_generation_plant_year`, out of `panel` | B14: 624 filers against 1,348 in 2024 (D-08) |
