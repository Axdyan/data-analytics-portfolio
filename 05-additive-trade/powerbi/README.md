# Power BI model

The dashboard is built in Power BI Desktop from the nine CSVs the notebook writes to
`data/powerbi/additive_trade/` (that folder is gitignored; the `.pbix` embeds its data).
Rebuild the CSVs by running the notebook's export cell, then Refresh in Desktop. Row counts
below are from the export of 2026-09-09.

The point of the model is to put the two joins side by side. The temporal join attaches to
every fact row the description its code carried in that month; the naive join attaches
whatever the code means today, and drops the row if the code means nothing today. Every
value measure exists in both forms, and the gap between them is a measure of its own.

## Star

| Table | Grain | Rows | Key | Role |
|---|---|---|---|---|
| `fct_imports_yearly_province` | one row per year, HS10 code, validity period, province of clearance | 3,301,776 | `year`, `hs10_period_key`, `province` | the fact for the corruption measures and the province role: `value_cad`, `source_rows`, `equijoin_status` |
| `fct_series_monthly` | one row per series and month | 5,800 | `series_key`, `ref_month` | the time axis: the additive manufacturing codes and baskets, and carbon fibre by regime |
| `dim_hs10` | one row per code and validity period | 53,570 | `hs10_period_key` | the validity dimension: `hs10`, `valid_from`, `valid_to`, `is_current`, `desc_en`, `current_desc_en`, `differs_from_current`, `meaning_changed`, `hs2`, `hs4`, `hs6` |
| `dim_hs10_current` | one row per code with an open period | 10,930 | `hs10` | the naive dimension, missing every code with no current meaning |
| `dim_year` | one row per year 1988 to 2026 | 39 | `year` | `year_start` as a real date, `from_2022` |
| `dim_date` | one row per month | 463 | `ref_month` | `year`, `month_no`, `month_name`, `quarter`, `year_month`, `from_2022` |
| `dim_province` | one row per province code | 14 | `province` | name in both languages; both NF and NL are here because both occur across the years |
| `dim_partner` | one row per partner country code | 263 | `partner_country` | name in both languages; not joined to the yearly fact, which is summed over partners, kept for the monthly series' future partner cut |
| `dim_series` | one row per series membership | 36 | `series_key`, `hs10`, `window_from` | `role`, `regime`, `rule`, `confidence`, `source_url`, `checked_on` |

Relationships, all one-to-many from the dimension, single direction:

- `dim_hs10[hs10_period_key]` to `fct_imports_yearly_province[hs10_period_key]`
- `dim_hs10_current[hs10]` to `fct_imports_yearly_province[hs10]`, **inactive**; the naive
  measures activate it with `USERELATIONSHIP` so both joins can be read off one fact
- `dim_year[year]` to `fct_imports_yearly_province[year]`
- `dim_province[province]` to `fct_imports_yearly_province[province]`
- `dim_date[ref_month]` to `fct_series_monthly[ref_month]`
- `dim_series[series_key]` to `fct_series_monthly[series_key]`, many-to-many because a series
  has one definition row per member code; use the regime and role columns as slicers only

Mark `dim_date` as the date table on `ref_month` and `dim_year` on `year_start`. Hide the key
columns on the facts. `equijoin_status` on the fact carries four values: `same`, `current
description differs`, `no current period`, `unmatched`.

## Measures

On `fct_imports_yearly_province`:

```
Import Value (temporal join) = SUM ( fct_imports_yearly_province[value_cad] )

Import Value (naive join) =
    CALCULATE (
        SUM ( fct_imports_yearly_province[value_cad] ),
        USERELATIONSHIP ( dim_hs10_current[hs10], fct_imports_yearly_province[hs10] ),
        NOT ISBLANK ( RELATED ( dim_hs10_current[hs10] ) )
    )

Misdescribed Value =
    CALCULATE ( [Import Value (temporal join)],
                fct_imports_yearly_province[equijoin_status] = "current description differs" )

Orphaned Value =
    CALCULATE ( [Import Value (temporal join)],
                fct_imports_yearly_province[equijoin_status] = "no current period" )

Corruption Value = [Misdescribed Value] + [Orphaned Value]

Corruption % = DIVIDE ( [Corruption Value], [Import Value (temporal join)] )

Misdescribed % = DIVIDE ( [Misdescribed Value], [Import Value (temporal join)] )

Codes Misdescribed =
    CALCULATE ( DISTINCTCOUNT ( fct_imports_yearly_province[hs10] ),
                fct_imports_yearly_province[equijoin_status] = "current description differs" )

Source Rows = SUM ( fct_imports_yearly_province[source_rows] )
```

The naive measure reads the same fact through the inactive relationship to the current
dimension, so a row whose code has no current period drops out, which is exactly what a join
on the code alone does. On the 1988 row of the year table the two value measures differ by
78 percent of the year; on 2026 they agree, because that year's dictionary is the current one.

On `fct_series_monthly`:

```
Series Value = SUM ( fct_series_monthly[value_cad] )

Series Value, trailing 12 =
    CALCULATE ( [Series Value],
                DATESINPERIOD ( dim_date[ref_month], MAX ( dim_date[ref_month] ), -12, MONTH ) )

YoY Growth =
    VAR ThisMonth = MAX ( dim_date[ref_month] )
    VAR Prior = CALCULATE ( [Series Value], DATEADD ( dim_date[ref_month], -12, MONTH ) )
    RETURN DIVIDE ( [Series Value] - Prior, Prior )

Regime Label = SELECTEDVALUE ( fct_series_monthly[regime], "additive manufacturing" )
```

Two caveats belong on the report canvas as text. `YoY Growth` on a carbon fibre series is
meaningless across a regime edge, and the regime slicer is there so a reader cannot draw one
without seeing which stretch they are in; a card showing `Regime Label` sits beside every
carbon fibre visual. And every value is nominal Canadian dollars at customs valuation; nothing
is deflated.

## Pages

1. **Two joins.** Card row: Import Value (temporal join), Import Value (naive join),
   Corruption %. Clustered column by `dim_year[year]` of Misdescribed Value and Orphaned Value
   stacked, with Import Value (temporal join) as a line on the same axis. A table under it by
   year with both value measures, Corruption %, Codes Misdescribed.
2. **What a code meant.** Slicer on `dim_hs10[hs10]` defaulting to 8485100000; a table of
   its periods from `dim_hs10` (valid_from, valid_to, desc_en, current_desc_en,
   differs_from_current); a column chart of Import Value (temporal join) by year for the code,
   coloured by `equijoin_status`. This is the propellers-to-printers page.
3. **The series.** Line of `Series Value` by `dim_date[ref_month]` for `series_key` in
   recipients, donors, combined, with a slicer on `fct_series_monthly[family]` and one on
   `regime`. Second visual: the carbon fibre series with the regime slicer, and the Regime
   Label card.
4. **By province.** Filled map or bar on `dim_province[province_name]` of Import Value
   (temporal join) and Corruption %, with the year slicer. This is the page the row-level
   security role is tested on.

## Row-level security

One role per province of clearance is enough to demonstrate the mechanism. In Desktop,
Modeling, Manage roles:

- Role `Province analyst ON`, table `dim_province`, filter `[province] = "ON"`.

Because the yearly fact hangs off `dim_province`, the filter propagates to every value and
corruption measure without a further rule. The monthly series fact is national and carries no
province, so it is unaffected by the role, and the page that shows it says so. Test with View
as. For a real deployment the role would read the viewer's identity through a mapping table on
`USERPRINCIPALNAME()` rather than a hard-coded province; the static role is the portfolio
version.

## Files

- `additive_trade.pbix` once built, committed here.
- Screenshots of each page as `page_1_two_joins.png`, `page_2_what_a_code_meant.png`,
  `page_3_series.png`, `page_4_province.png`.
