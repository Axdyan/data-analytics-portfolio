# Source to target

Every column the analysis reads, where it came from, what was done to it on the way, and the
check that guards it. Raw headers are quoted exactly as the source spells them. The raw
layer keeps every column as text, in Parquet for the imports and in DuckDB tables for the
dictionaries, and the casts happen in the dbt staging views, so a value that fails a cast is
visible beside its raw text rather than guessed at.

## Imports (`data/cimt/parquet/year=YYYY/imports.parquet` to `stg_cimt_imports` to `fct_imports_monthly`)

Source: the `ODPFN014` member of each yearly zip, converted by `python/backfill_cimt.py` with
every column as text and a row number, one Parquet file per year, 186,229,882 rows. The dbt
source reads the Parquet with hive partitioning, so `year` comes from the folder name.

| Raw header | Target | Transform | Guarding check |
|---|---|---|---|
| `YearMonth/AnnéeMois` | `ref_month`, first day of the month | `try_strptime` on `%Y%m`, cast to date | not_null on `ref_month`; C6 counts twelve distinct months per completed year in the run log |
| folder `year=YYYY` | `year` | hive partition, integer | not_null; C6 and C11 against the run log; the incremental fact is keyed on it |
| `HS10` | `hs10` | as text, ten digits | not_null; every row is ten digits; relationships to `dim_hs10` on the period key |
| `Country/Pays` | `partner_country` | as text, the two-letter code | not_null; `dim_lookups` carries the description |
| `Province` | `province` | as text | not_null; both NF and NL occur and both are in `dim_lookups` |
| `State/État` | `us_state` | `nullif` on the empty string | measured: no United States row without a state, no other row with one |
| `Value/Valeur` | `value_cad`, with `value_raw` beside it | `try_cast` to bigint | C7: 0 null, 0 negative; 1,403 exactly zero, kept |
| `Quantity/Quantité` | `quantity`, with `quantity_raw` | `try_cast` to bigint | C12: 71,985,063 rows zero with a positive value; not used downstream |
| `Unit of Measure/Unité de Mesure` | `uom` | as text | none; `N/A` where no quantity is reported |
| `file_row_number` | `parquet_row` | DuckDB's row number within the file | part of nothing; kept so a row can be found again |

Derived on `int_imports_with_validity` and carried into the fact:

| Target | Built from | Rule | Guarding check |
|---|---|---|---|
| `hs10_period_key` | `hs10`, `ref_month` against `int_hs10_validity` | left join on the code where `ref_month` lies between `valid_from` and `valid_to`; the key is the code plus the period's opening month | C5: the joined row count equals the staged count, so no row matched more than one period; C10: 0 rows matched none |
| `equijoin_status` | the period's `differs_from_current` and `current_desc_en` | `same` when the current description equals the period's; `current description differs`; `no current period`; `unmatched` | accepted_values; `mart_equijoin_corruption` sums value by bucket and year (C9) |

The fact is incremental by year with a delete-and-insert strategy; a plain run replaces the
latest year loaded, every year after it, and any year present in the source and absent from
the table. C8, uniqueness of month, code, partner, province and state, is a singular test
that groups one year at a time. A completeness check in the notebook compares the fact's row
count with staging on every build.

## The HS10 dictionary (`ODPF_1_HS10Desc.TXT` to `raw_hs10_dictionary` to `stg_hs10_dictionary` to `int_hs10_validity` to `dim_hs10`)

Source: the fixed-width file inside the 2026 zip, decoded as Windows-1252 and cut at measured
column positions by the notebook, written to `data/cimt/dictionary/hs10_desc.parquet` and
loaded as a raw table with every column as text. 53,570 rows.

| Raw field, columns | Target | Transform | Guarding check |
|---|---|---|---|
| code, 0 to 10 | `hs10`; `hs2`, `hs4`, `hs6` as prefixes | as text | C1: 0 lines fail the pattern; not_null |
| start month, 11 to 17 | `valid_from` | `try_strptime` on the month plus `01`, cast to date | not_null; C14: 0 nulls |
| end month, 18 to 24 | `valid_to` | the same, then `last_day`; 999912 becomes 9999-12-31 | not_null; C14; C2: 0 overlapping periods within a code |
| unit, 25 to 28 | `uom` | `nullif` on `N/A` | none |
| English, 29 to 111 | `desc_en` | as text, trimmed | not_null |
| French, 112 to 194 | `desc_fr` | as text, trimmed | none |
| file tag, 195 to 205 | `file_tag` | as text | none; documents the two fields the handoff's layout missed |
| snapshot month, 207 to 213 | `snapshot_month` | as text | compared across the eight kept snapshots |

Derived on `int_hs10_validity`:

| Target | Rule | Guarding check |
|---|---|---|
| `hs10_period_key` | `hs10` and `valid_from` as `YYYYMM` | unique, not_null |
| `version_no`, `n_versions` | row number and count over the code, ordered by `valid_from` | not_null; C3: 8,631 codes with more than one |
| `prior_desc_en`, `meaning_changed` | the previous period's description, and whether it differs | C4: 5,962 codes with more than one distinct description |
| `is_current`, `current_desc_en`, `differs_from_current` | the open period's description carried onto every period of the code | 10,930 open periods; 2,288 of them with a different past meaning |

`dim_hs10` is this table as the validity dimension, one row per code and period, in the shape
of a type 2 dimension built from the publisher's own ranges rather than from snapshots taken
here. `dim_hs10_current` keeps only the open periods and is the naive dimension the
dashboard compares against.

## The small lookups (`ODPF_6_CtyDesc.TXT`, `ODPF_7_StateDesc.TXT`, `ODPF_8_ProvDesc.TXT`, `ODPF_9_UOMDesc.TXT` to `stg_lookups` to `dim_lookups`)

Same layout without the unit column, 209 characters. 279, 55, 16 and 71 rows.

| Raw field | Target | Transform | Guarding check |
|---|---|---|---|
| code | `code`, and `code_number` where the country and province codes carry a number and a letter code in one field | `split_part` on the space | not_null; accepted_values on `lookup` |
| start and end month | `valid_from`, `valid_to`, `is_current` | as for the dictionary | not_null |
| English, French | `desc_en`, `desc_fr` | as text | none |

`dim_lookups` keeps the most recent row per lookup and code so the dashboard relationships are
one to many.

## The concordance (`conc-10-stats-2022.xlsx`, `conc-10-stats-2022-1.xlsx` to `crosswalks/concordance_202201.csv` to `int_concordance_202201`)

Source: the obsolete-to-new sheet of each spreadsheet, read from the second row, first and
third columns.

| Raw column | Target | Transform | Guarding check |
|---|---|---|---|
| `Obsolete HS10 Code` | `obsolete_hs10` | dots stripped, trimmed; text in the seed | every value ten digits; not_null; the singular test that every code ending 2021-12 appears |
| `New HS10 Code` | `new_hs10` | the same | every code starting 2022-01 appears |
| file name, URL, hash, pull date | `source_file`, `source_url`, `source_sha256`, `checked_on` | written by the notebook | none |

Derived on `int_concordance_202201`: `obsolete_desc_en` and `new_desc_en` from the dictionary
at each end, `same_code`, `mechanical_relation` (same code, subheading, heading, chapter, or
different chapter), `n_new_for_obsolete`, `n_obsolete_for_new` and `mapping_type` (one to one,
split, merge, many to many), with `pair_key` unique.

## The series definitions (`crosswalks/series_definitions.csv` to `mart_series_am`, `mart_series_carbon_fibre`)

Written by the notebook from the dictionary and the concordance, with a rule, a confidence
and a source on every row; 36 rows. Columns `series_key`, `role`, `hs10`, `window_from`,
`window_to`, `regime`. A row with no code is a window in which the goods had no code of their
own.

| Target | Built from | Rule | Guarding check |
|---|---|---|---|
| `mart_series_am`, one row per series and month | the fact summed over partner, province and state for each member code within its window; baskets summed over members | a basket starts at the first month every member exists; a month with no imports is a zero | unique `series_month_key`; not_null `value_cad`; the singular test that every code exists in the dictionary across its window |
| `mart_series_carbon_fibre`, one row per series and month from 1988 | the regime windows, and the fact summed over the coded members | value null where no code carries the goods, zero in a coded month with no imports | unique `series_month_key`; accepted_values on `regime`; the singular test that no carbon fibre window spans a change of description |
