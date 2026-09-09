# Data contract

What was pulled, from where, when, and what is known to be wrong with it. Every number here
was measured on the pull it describes. The publisher republishes whole years, so anything
quoted from this project carries the pull date, and a re-pull is expected to move the latest
year.

Two publishers. Statistics Canada's import files and their code dictionary, through the open
government catalogue, and the ten-digit concordance Statistics Canada prepared for the January
2022 tariff, published by the Canada Border Services Agency.

## 1. Canadian International Merchandise Trade, imports by HS10

| | |
|---|---|
| Publisher | Statistics Canada, catalogue 71-607-X, through open.canada.ca |
| Catalogue | eight packages, one per span of years, read with the catalogue's `package_show` call; full ids in `python/manifest.json` |
| Resource | one zip per year, `CIMT-CICM_Imp_YYYY.zip`, at `https://www150.statcan.gc.ca/n1/pub/71-607-x/2021004/zip/` |
| Member used | `ODPFN014_YYYYMMx.csv`, the HS10 file; the letter is C in the early years and N later |
| Grain | one row per month, ten-digit code, partner country, province of clearance and US state; state is blank unless the partner is the United States |
| Refresh | the current year is reissued as months are added; earlier years are republished as whole files |
| Pulled | the 2026 zip on 2026-09-05, the other thirty-eight on 2026-09-06 between 23:01 and 23:15 UTC |
| Licence | Open Government Licence, Canada |
| Bytes | 2.43 GB of zips, 1.03 GB of Parquet after conversion; per-year sizes and hashes in `python/run_log.csv` |
| Rows | 186,229,882 across 39 years and 463 months; by year from 1,091,139 in 1988 to 5,928,572 in 2025, and 3,418,311 for the seven months of 2026 |
| Manifest | `python/manifest.json`, written by the catalogue cell, last written 2026-09-07 |

Every zip carries the same three data files, at two, six and ten digits, and seven lookup
files. Only the ten-digit file is loaded; the coarser two are roll-ups of it.

Known defects, with the check that guards each:

- **The header carries accented French names.** `YearMonth/AnnéeMois`, `State/État`,
  `Quantity/Quantité`, `Unit of Measure/Unité de Mesure`. The backfill compares the header of
  every year against the expected list before converting; a file whose header differs stops
  the year and is logged.
- **A missing file can come back as HTML at HTTP 200.** The fetch refuses anything whose
  content type is not a zip or whose first four bytes are not the zip signature.
- **Value is never blank, non-integer or negative, on any of the 186 million rows** (C7). 1,403
  rows carry a value of exactly zero and are kept.
- **Quantity is zero on 71,985,063 rows that carry a positive value, 38.65 percent** (C12). The
  unit of measure is `N/A` on codes that report no quantity. Quantity is not used anywhere in
  this project.
- **The state column is consistent**: no United States row lacks a state and no other partner
  carries one, on every row.
- **Every code on every row is ten digits** and every code is in the dictionary (C10: 0
  unmatched rows).
- **Two spellings of one province.** NF and NL both appear across the years; both are kept in
  the lookup dimension.

## 2. The HS10 code dictionary

| | |
|---|---|
| Publisher | Statistics Canada, shipped inside every import zip as `ODPF_1_HS10Desc.TXT` |
| Layout | fixed width, 53,570 lines of exactly 213 characters, Windows-1252; eight fields at columns 0, 11, 18, 25, 29, 112, 195 and 207: code, start month, end month, unit, English, French, file tag, snapshot month |
| Grain | one row per code and validity period; 999912 marks an open period |
| Copy used | the one inside the 2026 zip, cut for July 2026, hash `aec32c0e1083fae9` |
| Rows | 53,570 code-periods, 42,771 distinct codes, 10,930 with an open period |
| Kept | every distinct snapshot the backfill met, under its hash, in `data/cimt/dictionary/snapshots/` |

The dictionary is a snapshot per zip. Eight distinct copies exist across the thirty-nine zips:

| Cut for | In the zips for | Code-periods | Periods only here | Periods only in the newest | Shared periods whose description changed |
|---|---|---|---|---|---|
| 2021-07 | 1988 to 2018 | 52,022 | 918 | 2,466 | 129 |
| 2021-12 | 2019 | 53,377 | 109 | 302 | 50 |
| 2022-12 | 2020 | 53,405 | 81 | 246 | 44 |
| 2023-12 | 2021 | 53,453 | 67 | 184 | 30 |
| 2024-12 | 2022 | 53,551 | 9 | 28 | 3 |
| 2025-12 | 2023 and 2024 | 53,570 | 0 | 0 | 2 |
| 2026-06 | 2025 | 53,570 | 0 | 0 | 0 |
| 2026-07 | 2026 | 53,570 | | | |

Known defects, with the check that guards each:

- **It is not a delimited file and it is not UTF-8.** A delimited reader takes the first line as
  a header; the bytes fail UTF-8 at position 327 and decode as Windows-1252. C1: 0 lines fail
  the measured pattern.
- **Two fields sit after the French description** that the handoff's six-field layout folded
  into it: a ten-character file tag and the month the snapshot was cut for.
- **The unit is `N/A` on codes that report no quantity**, and it is a text field like the rest
  at the raw layer.
- **No two periods of a code overlap** (C2: 0) and **every month converts to a date, the
  sentinel included** (C14: 0 nulls).
- **8,631 codes have more than one period and 5,962 more than one description** (C3, C4).
  The handoff, which read the 2023 copy, counted 5,924 descriptions and 2,280 active codes
  with a different past meaning; this copy has 5,962 and 2,288.
- **The four small lookups** for country, state, province and unit share the layout without
  the unit column, at 209 characters: 279, 55, 16 and 71 rows, 0 failed lines each.

## 3. The January 2022 statistical concordance

| | |
|---|---|
| Publisher | Statistics Canada, ten-digit statistical concordance, published by the Canada Border Services Agency on its Customs Tariff 2022 page |
| Files | `conc-10-stats-2022.xlsx`, 69,876 bytes, last modified 2021-12-06; `conc-10-stats-2022-1.xlsx`, the 2022-1 amendment, 28,530 bytes, last modified 2021-12-06 |
| Endpoint | `https://www.cbsa-asfc.gc.ca/trade-commerce/tariff-tarif/2022/concordance/` |
| Grain | one row per obsolete code and new code, on an obsolete-to-new sheet and its mirror |
| Pulled | 2026-09-07 |
| Rows | 2,052 pairs in the original and 455 in the amendment, 2,507 distinct pairs across both; 852 obsolete codes and 1,355 new codes |
| Kept | under `data/cimt/concordance/`, with the file, its hash and the pull date on every row of `crosswalks/concordance_202201.csv` |

Known defects and limits:

- **Codes are written with dots**, `0208.90.00.90`; the dots are stripped and every code is
  checked to be ten digits.
- **The original file alone is not complete.** 108 codes that end in December 2021 and 368
  that begin in January 2022, in chapters 27, 39, 42, 44, 63, 72, 73 and 85, appear only in
  the amendment. Together the two files cover every code at the break, which a dbt singular
  test asserts.
- **405 pairs in the original and 19 in the amendment map a code to itself**, a code that
  continues with a new description.
- **The mapping carries no weights.** 1,319 pairs sit in many-to-many groups and 906 in
  splits; the table says which codes fed a new code, not how much of each.

## What changed between pulls

The catalogue was read on 2026-09-05 and again on 2026-09-07, and the manifest did not change:
39 import zips, one per year, contiguous. The 2026 zip was pulled once, on 2026-09-05, and
covers January to July 2026; a later pull of that year is expected to add months and to
replace the file, and the backfill's log compares the hash and the row count so that the
change is recorded rather than silent. No other zip was pulled twice.
