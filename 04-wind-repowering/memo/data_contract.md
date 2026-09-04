# Data contract

What was pulled, from where, when, and what is known to be wrong with it. Every number here
was measured on the pull it describes. Both publishers revise their data, so anything quoted
from this project carries the pull date, and a re-pull is expected to move the counts.

Three sources: the current turbine database, its earliest archived release, and thirteen
years of plant-level generation. All three are US federal government publications with no
licence restriction stated.

## 1. US Wind Turbine Database, current release

| | |
|---|---|
| Publisher | US Geological Survey, with Lawrence Berkeley National Laboratory and the American Clean Power Association |
| Endpoint | `https://energy.usgs.gov/api/uswtdb/v1/turbines`, a PostgREST API; requested with `Accept: text/csv` and no filter, so every column and every row |
| Grain | one row per turbine, keyed on `case_id` |
| Refresh | several times a year. Repowered turbines are retired and reissued as new records with new ids, which the published changelog states and the join test confirmed (D-06) |
| Pulled | 2026-09-03 11:47 UTC |
| Last-Modified | not sent by the endpoint |
| Content type | `text/csv; charset=utf-8` |
| Bytes | 14,851,493 |
| SHA-256 | `ee1e259fd94489cd1fe3df36fffaa533afacf1d05e804eff68fcbed33540bd8e` |
| Rows, columns | 75,727 turbines, 28 columns |
| Manifest | `memo/pull_manifest.json`, written by the pull cell |

Counts that the study rests on, measured on this pull: 8,480 turbines flagged as retrofitted
and 67,247 not. Retrofit years 2015 (9), 2017 (1,317), 2018 (1,124), 2019 (1,893), 2020
(1,744), 2021 (736), 2022 (833), 2023 (460), 2024 (364); no 2016 and no null years. Rolled
up to plants with an `eia_id`: 1,327 plants, of which 90 are entirely retrofitted, 1,208
untouched, and 29 hold both.

Known defects, with the assertion that guards each:

- **No field records blade material, fibre or construction** (no assertion; a limit of the
  source). The nearest thing is manufacturer and model, which is an inference, not a record.
- **`case_id` is not stable across releases.** Only 894 of the 8,480 retrofitted turbines
  (10.5%) carry an id that appears in the April 2018 file, and the 2018, 2019, 2022 and
  2023 cohorts match at 0%. The project id `usgs_pr_id` bridges 7,820 (92.2%) and is the key
  used instead (D-06).
- **`p_year` is rewritten to the repowering year on 1,529 retrofitted turbines across 17
  plants** (B5). The column means "build year" on most rows and "repowering year" on those,
  with no flag. Thirteen of the 17 plants are in the treated group; they do not set the
  vintage window.
- **`eia_id` missing on 3,615 turbines, 4.8%** (B2), carrying 3,766 MW, 2.4% of capacity.
  Only 40 of them are retrofitted. They cannot be joined to generation and are out.
- **Nulls on `t_cap` 3,282 (4.3%), `t_rd` 3,527 (4.7%), `p_year` 1,125 (1.5%)** (B3), kept as
  null. 170 plant-years in the generation file carry zero or negative net generation (B9).
- **13 project ids span two plants.** They are excluded from the bridge to the 2018 file so
  that no capacity or rotor is attributed to the wrong plant.

## 2. US Wind Turbine Database, April 2018 release

| | |
|---|---|
| Publisher | as above; the ScienceBase catalogue holds the legacy releases as separate items |
| Endpoint | `https://www.sciencebase.gov/catalog/file/get/5e99a01082ce172707f6fd2a?name=uswtdb_v1_0_20180419.zip` |
| Grain | one row per turbine as of April 2018 |
| Refresh | never; it is an archived snapshot |
| Pulled | 2026-09-03 |
| Bytes | 5,109,809 for the archive, matching the catalogue's stated size; the CSV member is 10,559,773 bytes |
| Rows, columns | 57,636 turbines, 24 columns |
| Used for | the pre-repowering capacity and rotor baselines only |

Known defects:

- **No `eia_id`.** The file cannot reach the generation data at all. It reaches a plant only
  through `usgs_pr_id` and the current file's mapping from project to plant.
- **Missing numbers are coded `-9999`, never null**: 5,137 rows on `t_rd`, 3,041 on `t_cap`,
  113 on `p_year`. Missing strings are the word `missing`. Every aggregate over this file
  excludes the sentinel explicitly and counts it.
- **Column drift against the current release**: `t_img_srce` here is `t_img_src` today, and
  the current file's `eia_id`, `t_retrofit`, `t_retro_yr` and `t_offshore` do not exist here.
- **Coverage on the study plants** (B15): the bridge reaches 565 of 567 eligible controls and
  83 of 90 treated plants for capacity; for rotor diameter on both sides, 4 of the 80 treated
  plants in the estimate have no record.

## 3. EIA-923, plant-level generation, 2013 to 2025

| | |
|---|---|
| Publisher | US Energy Information Administration, Form EIA-923 |
| Endpoint | `https://www.eia.gov/electricity/data/eia923/archive/xls/f923_YYYY.zip` for past years; the year in progress sits at `.../eia923/xls/f923_YYYY.zip` without `archive/` |
| Grain | one row per plant, prime mover and fuel per year, with twelve monthly columns and an annual total; this project keeps rows where the reported fuel type is `WND` and sums them to the plant-year |
| Refresh | annual final revisions; the latest year is provisional and reissued |
| Pulled | 2026-09-03, thirteen archives |
| Bytes | 2013: 18,854,113; 2014: 20,951,748; 2015: 20,071,619; 2016: 19,648,061; 2017: 21,584,197; 2018: 21,305,966; 2019: 21,885,522; 2020: 21,465,660; 2021: 22,281,584; 2022: 22,871,857; 2023: 22,359,936; 2024: 22,755,334; 2025: 19,708,197 |
| Workbook | the member matching `Schedules_2_3_4_5`, one per archive: `EIA923_Schedules_2_3_4_5_2013_Final_Revision.xlsx`, then `..._M_12_YYYY_Final_Revision.xlsx` for 2014 to 2023, `..._M_12_2024_Final.xlsx`, and `..._M_12_2025_20FEB2026.xlsx` |
| Sheet, header | `Page 1 Generation and Fuel Data`, header on row index 5, 97 columns in every year |
| Rows | 14,203 wind rows across the range; 14,077 plant-years over 1,486 plants after quarantine and roll-up |

Known defects, with the assertion or decision that handles each:

- **A missing file answers with a web page at HTTP 200.** Requesting a past year from the
  current-year folder returns the section landing page, about 57 KB of HTML, with a success
  status. The fetch checks the content type and the first four bytes (`PK` followed by
  `0x03 0x04`) before writing anything.
- **HEAD and GET disagree.** The same archive URL answers 503 to HEAD and 200 to GET, so
  availability cannot be probed with HEAD.
- **Header text wraps inside the cell in later years**, so the same column reads differently
  by year. Whitespace is collapsed before names are compared (B8).
- **2013 spells two things differently**: `State` for `Plant State`, and `Netgen_Jan` to
  `Netgen_Dec` for `Netgen January` to `Netgen December`. The rename map covers exactly
  these, and the required-column check runs on every year (B8).
- **A dot is the missing-value marker.** It appears in the `YEAR` column on 19 wind rows and
  is not null, so nothing catches it until a cast fails. Those rows are in
  `dq_generation_quarantine` (B16). `Plant Id` is clean on every row.
- **The twelve monthly columns and the annual total agree** on every row to within 1 MWh
  (B17), so the annual column is used without adjustment.
- **11 plant-years are built from more than one wind row** (B12), summed.
- **2025 is a provisional release** (B14, D-08): 624 plants filed against 1,348 in 2024, with
  every month populated for those that filed (663 rows in January rising to 687 in December,
  the same shape as 2024). It is missing filers, not months. Its national total is higher
  than 2024's because the large plants are the ones that have filed. It stays in the fact
  table and out of the panel.
- **The 2026 file** covers months through June 2026 and was not pulled; the panel is annual.

## What changed between pulls

One pull of each source was made, on 2026-09-03, and every number in this project comes
from it. A second pull at the end of the build has not been run. When it is, the turbine
pull cell rewrites the manifest and the differences to record here are: the byte count and
hash, the turbine count, the retrofit counts by year, and the plant counts by status. The
generation archives are annual and are not expected to change until the next revision cycle;
the one that will is 2025, whose final revision should restore most of the 754 absent filers
and with them the 2024 treatment cohort's post-period.
