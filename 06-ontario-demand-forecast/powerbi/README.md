# Power BI model

The dashboard is built in Power BI Desktop from the seven CSVs the notebook writes to
`data/powerbi/ontario_demand/` (that folder is gitignored; the `.pbix` embeds its data).
Rebuild the CSVs by running the notebook's export cell, then Refresh in Desktop.

## Star

| Table | Grain | Key | Role |
|---|---|---|---|
| `fct_demand_hourly` | one row per hour from May 2002 to the window end | `ts_start`; `date` to the calendar | the actual series: `ontario_mw`, `market_mw`, and `filled`, true on the one hour the source omits and the notebook interpolates |
| `fct_forecast` | one row per origin day, lead hour and model over the test window | `origin_date`, `lead_hours`, `model`; `target_date` to the calendar | the scored forecasts: `forecast_mw`, `actual_mw`, `error_mw`, and the 80% and 95% bands `lo80`, `hi80`, `lo95`, `hi95` (blank on the last-day baseline, which has no bands) |
| `fct_demand_zonal` | one row per hour and zone from January 2024 | `ts_start`, `zone_key`; `date` to the calendar | zonal demand for the dashboard's map and for the row-level-security role |
| `dim_date` | one row per date | `date` | year, month, day of year, ISO weekday, `holiday_name`, `day_type` (weekday, saturday, sunday, holiday), and the May-to-April `ici_base_period` |
| `dim_zone` | one row per zone | `zone_key` | the ten IESO zones with a display name |
| `dim_model` | one row per forecast | `model` | `model_kind` (baseline or model) and a one-line description |
| `dim_lead` | one row per lead hour, 1 to 168 | `lead_hours` | `target_day` (1 to 7), `target_hour_ending`, and `lead_bucket` (day ahead, two days ahead, days 3 to 6, week ahead) |

Relationships, all one-to-many from the dimension, single direction:

- `dim_date[date]` to `fct_demand_hourly[date]`
- `dim_date[date]` to `fct_forecast[target_date]`, active. A second relationship to
  `fct_forecast[origin_date]` is created inactive and reached with `USERELATIONSHIP`
  where a visual is about when the forecast was issued rather than what it was about.
- `dim_date[date]` to `fct_demand_zonal[date]`
- `dim_zone[zone_key]` to `fct_demand_zonal[zone_key]`
- `dim_model[model]` to `fct_forecast[model]`
- `dim_lead[lead_hours]` to `fct_forecast[lead_hours]`

Mark `dim_date` as the date table on `date`. Hide the key columns on the facts. Set
`ts_start` and `target_ts` to the Date/Time type; they are on a fixed standard-time clock
with no daylight-saving shift, and the report should say so where an hour is shown.

## Measures

Create these on `fct_forecast` unless noted.

```
Actual Demand (MW) = AVERAGE ( fct_demand_hourly[ontario_mw] )

Peak Demand (MW) = MAX ( fct_demand_hourly[ontario_mw] )

Energy (GWh) = DIVIDE ( SUM ( fct_demand_hourly[ontario_mw] ), 1000 )

Forecasts Scored = COUNTROWS ( fct_forecast )

MAE (MW) = AVERAGEX ( fct_forecast, ABS ( fct_forecast[error_mw] ) )

Bias (MW) = AVERAGE ( fct_forecast[error_mw] )

RMSE (MW) = SQRT ( AVERAGEX ( fct_forecast, fct_forecast[error_mw] ^ 2 ) )

MAPE (%) =
    AVERAGEX ( fct_forecast, DIVIDE ( ABS ( fct_forecast[error_mw] ), fct_forecast[actual_mw] ) )

Naive MAE (MW) = CALCULATE ( [MAE (MW)], dim_model[model] = "seasonal naive" )

Model MAE (MW) = CALCULATE ( [MAE (MW)], dim_model[model] = "linear model" )

Skill vs Naive (%) = DIVIDE ( [Naive MAE (MW)] - [Model MAE (MW)], [Naive MAE (MW)] )

Coverage 80 (%) =
    AVERAGEX (
        FILTER ( fct_forecast, NOT ISBLANK ( fct_forecast[lo80] ) ),
        IF ( fct_forecast[actual_mw] >= fct_forecast[lo80] && fct_forecast[actual_mw] <= fct_forecast[hi80], 1, 0 )
    )

Coverage 95 (%) =
    AVERAGEX (
        FILTER ( fct_forecast, NOT ISBLANK ( fct_forecast[lo95] ) ),
        IF ( fct_forecast[actual_mw] >= fct_forecast[lo95] && fct_forecast[actual_mw] <= fct_forecast[hi95], 1, 0 )
    )

Band Width 80 (MW) =
    AVERAGEX ( FILTER ( fct_forecast, NOT ISBLANK ( fct_forecast[lo80] ) ), fct_forecast[hi80] - fct_forecast[lo80] )

Peak Error (MW) =
    VAR ActualPeak = MAXX ( fct_forecast, fct_forecast[actual_mw] )
    VAR ForecastPeak = MAXX ( fct_forecast, fct_forecast[forecast_mw] )
    RETURN ForecastPeak - ActualPeak

Zone Demand (MW) = AVERAGE ( fct_demand_zonal[zone_mw] )

Zone Peak (MW) = MAX ( fct_demand_zonal[zone_mw] )
```

Three caveats belong on the report canvas as text, not in a tooltip. `Skill vs Naive`
is only meaningful when the visual is filtered to the same leads for both models, which
the `dim_lead` slicer guarantees and a free-form filter on `fct_forecast` does not. `Peak
Error` is a daily quantity: it is right when the visual's context is one origin day and
the day-ahead bucket, and it is a number without a meaning at any other grain. And the
coverage measures ignore the last-day baseline because that baseline carries no bands, so a
visual split by model shows two bars, not three.

## Pages

1. **Demand.** Card row: Actual Demand, Peak Demand, Energy. Line: Actual Demand by
   `dim_date[date]` at month grain with the `day_type` slicer. Table under it: year, peak,
   the peak's date from `fct_demand_hourly`, energy.
2. **Forecast skill.** Line: MAE (MW) by `dim_lead[lead_hours]`, legend on
   `dim_model[model]`, one y axis. Matrix: MAE (MW) by `dim_lead[lead_bucket]` against
   `dim_model[model]`, with Skill vs Naive as a third column. Cards: Model MAE, Naive MAE,
   Skill vs Naive, all under the `lead_bucket` slicer.
3. **Calibration.** Line: Coverage 80 and Coverage 95 by `dim_date[date]` at month grain,
   the relationship being on the target date, with constant lines at 80 and 95. Card: Band
   Width 80. Slicer on `dim_model[model]`. Second line: Bias (MW) by month, to show where the
   model under-calls.
4. **Peak days.** Table of the highest `Peak Demand` days from `fct_demand_hourly`, each
   with its `ici_base_period`, and beside it Peak Error for the same days from the
   day-ahead forecasts, using the inactive relationship on `origin_date`.
5. **Zones.** Filled map on `dim_zone[zone_name]` with `Zone Demand` as the colour, and a
   line of `Zone Peak` by month. This is the page the security role changes.

## Row-level security

One role per zone is enough to demonstrate the mechanism. In Desktop, Modeling, Manage
roles:

- Role `Zone analyst Toronto`, table `dim_zone`, filter `[zone_key] = "toronto"`.

The filter propagates through `dim_zone` to `fct_demand_zonal` and nothing else, so a
viewer in the role sees one zone's demand and the full provincial series and forecasts,
which is the intended behaviour: the forecast is a provincial product. Test it with View
as. For a real deployment the role would read the viewer's identity through a mapping
table on `USERPRINCIPALNAME()` rather than a hard-coded zone; the static role is the
portfolio version.

## Files

- `ontario_demand.pbix` once built, committed here.
- Screenshots of each page as `page_1_demand.png`, `page_2_skill.png`,
  `page_3_calibration.png`, `page_4_peaks.png`, `page_5_zones.png`.
