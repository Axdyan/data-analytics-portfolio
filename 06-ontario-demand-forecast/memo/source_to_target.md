# Source to target

Every column the analysis reads, where it came from, what was done to it on the way, and
the check that guards it. Raw headers are quoted exactly as the source spells them. Both
report families load with every column as text, on purpose: the publisher writes one
column with a quoted thousands separator, and a type guess would either split the row or
turn the value into a null without saying so. Casts happen in the staged tables, where a
failure is a null that gets counted.

Check ids refer to the assertion table the notebook renders as `dq_assertions`.

## Hourly demand (`PUB_Demand_YYYY.csv` to `raw_demand`, `stg_demand_hourly`, `fct_demand_hourly`)

Source: IESO public reports, one file per year from 2002, three metadata lines then a
header then one row per hour. The metadata lines are skipped by count after the header of
every file is compared with the expected one (B2) and the year written inside the file is
compared with the year in its name (B3).

| Raw header | Target | Transform | Guarding check |
|---|---|---|---|
| `Date` | `stg_demand_hourly.date`; `fct_demand_hourly.date` | `TRY_CAST` to `DATE` | cast failures counted in the staging cell; B1 checks the (date, hour) key is unique |
| `Hour` | `stg_demand_hourly.hour_ending` | `TRY_CAST` to `INTEGER`; published as 1 to 24 and meaning the hour ending, kept as published | B6 counts dates with other than 24 rows before the window end |
| `Date`, `Hour` together | `ts_start` | date as a timestamp plus (hour minus one) hours: the start of the hour, the key every lag and join uses | B5 counts hours missing from a generated spine; B14 blocks if any day of the test window is absent |
| `Ontario Demand` | `stg_demand_hourly.ontario_mw`; `fct_demand_hourly.ontario_mw` | `TRY_CAST` to `INTEGER`; the forecast target | B4 counts failed casts; B8 counts hours below half of the same hour a week earlier, which finds the August 2003 blackout and nothing else |
| `Market Demand` | `stg_demand_hourly.market_mw`; `fct_demand_hourly.market_mw` | `TRY_CAST` to `INTEGER`; carried for the dashboard, not used by the model | B7 counts hours where it sits below Ontario demand |
| the file name | `source_file` | the yearly file each row came from | none; used to reconcile rows per file against the rows a complete year holds |

Derived on `fct_demand_hourly`:

| Target | Rule | Guarding check |
|---|---|---|
| the row set | every hour on a generated spine from the first to the last published hour, left-joined to the staged rows | B5, B10 |
| `ontario_mw`, `market_mw` on a spine hour with no source row | the mean of the hour before and the hour after, rounded | B10 counts the filled rows and expects the same number B5 found |
| `filled` | true where the source had no row for the hour | carried into the export so a dashboard can exclude it |
| `hour_ending` | the hour of `ts_start` plus one | |
| calendar columns | joined from `dim_date` on the date | B9 blocks if any date has no calendar row |

## Holiday calendar (`crosswalks/ontario_holidays.csv` to `xw_holidays`, `dim_date`)

Source: computed in the notebook from Ontario's holiday rules (fixed dates, nth-weekday
rules, the Monday before May 25, Easter arithmetic for Good Friday), then merged with the
committed file so that a reviewed row is never overwritten.

| Column | Target | Rule | Guarding check |
|---|---|---|---|
| `holiday_name` | `dim_date.holiday_name` | the name, joined on the observed date | |
| `actual_date` | not carried | the calendar date of the holiday | |
| `observed_date` | join key to `dim_date.date` | the actual date, moved forward to the next weekday not already taken when it falls on a weekend or collides with another holiday | B9 |
| `statutory` | not carried | false only for the Civic Holiday, which Ontario does not legislate but most of the province takes | |

Derived on `dim_date`:

| Target | Rule |
|---|---|
| `day_type` | `holiday` where a holiday is observed, else `saturday`, `sunday` or `weekday` by ISO weekday |
| `iso_dow` | 1 for Monday to 7 for Sunday |
| `day_of_year` | 1 to 366, the argument of the annual sine and cosine terms |
| `ici_base_year`, `ici_base_period` | the May-to-April period the date falls in, labelled by its starting year, `2025-26` for May 2025 to April 2026 |

## Forecast arrays (`fct_demand_hourly` to `D`, `A`, `F_naive`, `F_last`, `F_model`, `fct_forecast`)

The hourly series up to the window end is reshaped to one row per day and one column per
hour. Every array below is indexed by origin day (rows) and lead hour 1 to 168 (columns).

| Target | Rule | Guarding check |
|---|---|---|
| `A` | the actual demand at every target hour of the seven days after the origin | the reshape raises if the hour count is not a whole number of days |
| `F_naive` | the demand at the same hour seven days before the target, which is at or before the origin for every lead | none needed; it is a lookup |
| `F_last` | the origin day's 24 hours repeated seven times | |
| `X` | sixteen features per origin and lead: a constant, the same hour one and two weeks before the target, the same hour on the origin day, the mean of the origin day, the mean of the origin week, the last hour before the origin, the target day's Saturday, Sunday and holiday flags, and three sine and cosine pairs on the target day's day of year | the cell prints whether any feature is null |
| `F_model` | one least squares fit per lead every 28 origins on the five years of origins whose targets were all observed before the block, applied to the block's origins | B16 blocks if any scored origin lacks a forecast |
| `lo80`, `hi80`, `lo95`, `hi95` | the point forecast plus the 10th and 90th, or 2.5th and 97.5th, percentiles of that lead's residuals over the 365 origins ending seven days before the origin, computed separately for the naive and the model | coverage is measured, not assumed, in the calibration cells |
| `fct_forecast` | the arrays above for test origins only, one row per origin, lead and model, with `target_ts`, `target_date`, `actual_mw`, `error_mw` as forecast minus actual | B15 reconciles the export row count against the table |

## Zonal demand (`PUB_DemandZonal_YYYY.csv` to `raw_zonal`, `stg_zonal_hourly`, `fct_demand_zonal`)

Source: IESO public reports, one file per year from 2003, the same three metadata lines,
then fifteen columns. Loaded with the quote character set explicitly, because the
difference column is written as `"-1,054"` when it reaches four digits and a sniffed
dialect splits that into two fields.

| Raw header | Target | Transform | Guarding check |
|---|---|---|---|
| `Date`, `Hour` | `date`, `hour_ending`, `ts_start` | as for the hourly demand file | |
| `Ontario Demand` | `stg_zonal_hourly.ontario_mw` | comma removed, `TRY_CAST` to `INTEGER` | B18 blocks on any failed cast |
| `Northwest`, `Northeast`, `Ottawa`, `East`, `Toronto`, `Essa`, `Bruce`, `Southwest`, `Niagara`, `West` | one column each in `stg_zonal_hourly`; unpivoted to `fct_demand_zonal.zone_key`, `zone_mw` | comma removed, `TRY_CAST` to `INTEGER`; the fact keeps January 2024 onward | B11 counts rows where the ten zones do not sum to the published total; the cell prints the largest gap and how many exceed 5 MW |
| `Zone Total` | `stg_zonal_hourly.zone_total` | comma removed, `TRY_CAST` to `INTEGER` | B11 |
| `Diff` | `stg_zonal_hourly.diff` | comma removed, `TRY_CAST` to `INTEGER` | B17 counts rows written with a thousands separator; B12 counts rows where zone total minus Ontario demand is not the published difference |

`dim_zone` is written from the ten zone names; `dim_model` and `dim_lead` are written from
the design constants. Every export is read back and its line count compared with the
source table (B15).
