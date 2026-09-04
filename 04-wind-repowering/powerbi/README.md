# Power BI model

The dashboard is built in Power BI Desktop from the four CSVs the notebook writes to
`data/powerbi/wind_repowering/` (that folder is gitignored; the `.pbix` embeds its data).
Rebuild the CSVs by running the notebook's export cell, then Refresh in Desktop.

## Star

| Table | Grain | Key | Role |
|---|---|---|---|
| `fct_generation_plant_year` | one row per plant and year | `plant_id`, `year` | the fact: `net_gen_mwh`, `rows_summed`, `source_file` |
| `fct_turbine` | one row per turbine | `case_id`; `plant_id` to the plant | turbine detail: capacity, hub height, rotor, retrofit flag and year, coordinates |
| `dim_plant` | one row per plant | `plant_id` | status (treated, control, mixed), cohort year, build year, rotor class, `in_study` |
| `dim_date` | one row per year 2013 to 2025 | `year` | `year_start` as a real date, `provisional` true on 2025 |

Relationships, all one-to-many from the dimension, single direction:

- `dim_plant[plant_id]` to `fct_generation_plant_year[plant_id]`
- `dim_plant[plant_id]` to `fct_turbine[plant_id]`
- `dim_date[year]` to `fct_generation_plant_year[year]`

Mark `dim_date` as the date table on `year_start`. Hide the key columns on the facts.

## Measures

Create these on `fct_generation_plant_year` unless noted.

```
Net Generation (MWh) = SUM ( fct_generation_plant_year[net_gen_mwh] )

Plants Reporting = DISTINCTCOUNT ( fct_generation_plant_year[plant_id] )

Generation per Plant (GWh) =
    DIVIDE ( [Net Generation (MWh)] / 1000, [Plants Reporting] )

Turbines Today =
    SUMX ( VALUES ( dim_plant[plant_id] ), CALCULATE ( SUM ( dim_plant[n_turbines] ) ) )

Capacity Today (MW) =
    SUMX ( VALUES ( dim_plant[plant_id] ), CALCULATE ( SUM ( dim_plant[total_cap_mw] ) ) )

Generation per Turbine (MWh) = DIVIDE ( [Net Generation (MWh)], [Turbines Today] )

Generation per MW (MWh) = DIVIDE ( [Net Generation (MWh)], [Capacity Today (MW)] )

YoY Change =
    VAR ThisYear = MAX ( dim_date[year] )
    VAR Prior = CALCULATE ( [Net Generation (MWh)], dim_date[year] = ThisYear - 1 )
    RETURN DIVIDE ( [Net Generation (MWh)] - Prior, Prior )

Treated Generation (MWh) =
    CALCULATE ( [Net Generation (MWh)], dim_plant[status] = "treated", dim_plant[in_study] = TRUE () )

Control Generation (MWh) =
    CALCULATE ( [Net Generation (MWh)], dim_plant[status] = "control", dim_plant[in_study] = TRUE () )

Treated Plants =
    CALCULATE ( DISTINCTCOUNT ( dim_plant[plant_id] ), dim_plant[status] = "treated" )

Cohort Size =
    CALCULATE ( DISTINCTCOUNT ( dim_plant[plant_id] ), dim_plant[status] = "treated", dim_plant[in_study] = TRUE () )
```

Two caveats belong on the report canvas as text, not in a tooltip. Capacity and turbine
count come from the current turbine release, so "per MW" and "per turbine" divide every
year's generation by today's machine, which for a repowered plant is the post-repowering
machine. And 2025 is a provisional release with about half the filers, so `YoY Change` on
2025 is a reporting artefact; the `provisional` flag on `dim_date` is there to grey it out.

## Pages

1. **Fleet.** Card row: Net Generation, Plants Reporting, Treated Plants. Line: Net
   Generation by `dim_date[year_start]`, split by `dim_plant[status]`. Slicer on
   `dim_plant[in_study]`.
2. **Where repowering happened.** Filled map on `dim_plant[state]` with `Treated Plants`
   as the colour saturation, tooltip showing `Cohort Size` and `Capacity Today (MW)`.
   Table under it: state, treated plants, control plants in the study, capacity.
3. **Treated against control.** Line of `Treated Generation (MWh)` and
   `Control Generation (MWh)` indexed to 2013 (a calculated measure dividing by the
   2013 value), and a matrix of `Cohort Size` by `cohort_year` and `rotor_class`.

## Row-level security

One role per state is enough to demonstrate the mechanism. In Desktop, Modeling, Manage
roles:

- Role `State analyst TX`, table `dim_plant`, filter `[state] = "TX"`.

Because every fact hangs off `dim_plant`, the filter propagates to generation and
turbines without any further rule. Test it with View as. For a real deployment the role
would read the viewer's identity through a mapping table on `USERPRINCIPALNAME()`
rather than a hard-coded state; the static role is the portfolio version.

## Files

- `wind_repowering.pbix` once built, committed here.
- Screenshots of each page as `page_1_fleet.png`, `page_2_map.png`, `page_3_comparison.png`.
