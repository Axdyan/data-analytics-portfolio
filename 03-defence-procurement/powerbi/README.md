# Power BI model

The same numbers as the memo, in a star schema, so that a reader with Power BI
can slice them rather than take them from a table. Import mode from the CSVs the
notebook writes under `data/canadabuys/powerbi_export/`, which is gitignored; the
`.pbix` embeds the rows.

## The star

Two fact tables share five dimensions. Every key is an integer or a short code,
and no exported field spans a line, because the raw UNSPSC field runs to 289
characters with newlines inside it and the default text import would split a
quoted multi-line key into two rows.

| Table | Grain | Rows | Notes |
|---|---|---:|---|
| `fct_contract` | One row per contract at its latest amendment | 13,295 | The one negative contract is quarantined out. Carries `instrument_type`, `has_original_row`, `is_cw_reference` and `value_flag` for slicing. |
| `fct_contract_amendment` | One row per source row | 21,889 | Kept so the naive sum can be shown beside the keyed one. Carries the contract total only; the amendment amount stays out of the model because it has no aggregate meaning. |
| `dim_supplier` | One row per supplier name key | 6,227 | `control_class`, `ultimate_parent`, `parent_country_iso2`, confidence and check date from the published crosswalk. Unresearched suppliers are `unresolved`. |
| `dim_country` | One row per resolved ISO code | 34 | `is_canada`, `country_name`, and `raw_values` showing which spellings collapsed into the row. `UNKNOWN` is an explicit member. |
| `dim_end_user` | One row per raw end-user string | 341 | `is_dnd` is the defence flag, a substring test, since one string can name up to 25 bodies. |
| `dim_unspsc` | One row per distinct raw code string | 2,755 | Integer `unspsc_key`; `segment`, `family`, `class_code`, `codes_on_contract`. Key 0 is an explicit `unclassified` member. |
| `dim_date` | One row per day, whole calendar years | 1,461 | 2023-01-01 to 2026-12-31. Federal fiscal year April to March, labelled by its end year and as `2024-25`. |

The notebook prints a reconciliation after writing the files: source rows,
exported rows, rows dropped, and the line count of each file. The only rows
dropped are the negative contract's, one in each fact, and any file whose line
count disagrees with its row count stops the notebook.

## Relationships

All single-direction, one-to-many, from the dimension to each fact.

| From | To | |
|---|---|---|
| `dim_supplier[supplier_key]` | `fct_contract[supplier_key]`, `fct_contract_amendment[supplier_key]` | |
| `dim_country[iso2]` | `fct_contract[iso2]`, `fct_contract_amendment[iso2]` | |
| `dim_end_user[end_user_key]` | `fct_contract[end_user_key]`, `fct_contract_amendment[end_user_key]` | |
| `dim_unspsc[unspsc_key]` | `fct_contract[unspsc_key]`, `fct_contract_amendment[unspsc_key]` | Integer key, not the raw code string. |
| `dim_date[date_key]` | `fct_contract[latest_award_date]`, `fct_contract_amendment[award_date]` | Active. Mark `dim_date` as the date table. |
| `dim_date[date_key]` | `fct_contract_amendment[amendment_date]` | Inactive; use through `USERELATIONSHIP` for a timeline of amendments rather than of awards. |

Undated contracts, 285 of them, have no day to join to and fall into the blank
member of `dim_date`. That is the decision on record in the notebook, and the
blank should be left visible rather than filtered away.

## Measures

Created on `fct_contract`, one at a time.

```
Keyed Value = SUM ( fct_contract[contract_value_cad] )

Naive Value = SUM ( fct_contract_amendment[contract_value_cad] )

Overstatement = [Naive Value] - [Keyed Value]

Overstatement % = DIVIDE ( [Overstatement], [Keyed Value] )

Contract Count = COUNTROWS ( fct_contract )

Canadian Value (Address) =
    CALCULATE ( [Keyed Value], dim_country[is_canada] = TRUE () )

Canadian Share (Address) = DIVIDE ( [Canadian Value (Address)], [Keyed Value] )

Canadian Share (Control, lower) =
    DIVIDE (
        CALCULATE (
            [Keyed Value],
            dim_country[is_canada] = TRUE (),
            dim_supplier[control_class] = "canadian_controlled"
        ),
        [Keyed Value]
    )

Canadian Share (Control, upper) =
    DIVIDE (
        CALCULATE (
            [Keyed Value],
            dim_country[is_canada] = TRUE (),
            dim_supplier[control_class] IN { "canadian_controlled", "unresolved" }
        ),
        [Keyed Value]
    )

Control Coverage % =
    DIVIDE (
        CALCULATE ( [Canadian Value (Address)], dim_supplier[control_class] <> "unresolved" ),
        [Canadian Value (Address)]
    )

Canadian Share by Count =
    DIVIDE (
        CALCULATE ( [Contract Count], dim_country[is_canada] = TRUE () ),
        [Contract Count]
    )

Top 3 Share =
    VAR t = TOPN ( 3, VALUES ( dim_supplier[supplier_key] ), [Keyed Value] )
    RETURN DIVIDE ( CALCULATE ( [Keyed Value], t ), [Keyed Value] )

HHI =
    SUMX (
        VALUES ( dim_supplier[supplier_key] ),
        POWER (
            100 * DIVIDE ( [Keyed Value], CALCULATE ( [Keyed Value], ALLSELECTED ( dim_supplier ) ) ),
            2
        )
    )
```

What to expect with no filters applied, from the notebook's own figures on the
2026-09-03 pull: Keyed Value $66,363,740,301.42, Naive Value
$132,853,897,948.13, Overstatement % 100.2%, Contract Count 13,295, Canadian
Share (Address) 89.13%. Filtered to `dim_end_user[is_dnd] = TRUE`: Keyed Value
$19,878,465,949.91, Canadian Share (Address) 78.17%, Control lower 24.16%,
Control upper 41.04%, Control Coverage 78.41%. A card that disagrees with those
means a relationship is wrong, not that the data moved.

Control Coverage % is the guard on the two control measures. Below 50% the
range between lower and upper is an artefact of how little was researched, and
the notebook's marts refuse to interpret it there. The report should carry the
coverage card beside the control cards for the same reason.

## Row-level security

One role, the department-viewer pattern.

| Role | Table | Filter |
|---|---|---|
| `DND viewer` | `dim_end_user` | `[is_dnd] = TRUE()` |

The filter propagates through the single-direction relationships to both facts.
View as role and the Keyed Value card should read $19,878,465,949.91.

## Report page

- Cards: Keyed Value, Naive Value, Overstatement %, Contract Count.
- Bar: Canadian Share (Address), Canadian Share (Control, lower) and Canadian
  Share (Control, upper) by `dim_end_user[is_dnd]`, with Control Coverage %
  beside it.
- Table: top suppliers by Keyed Value with `control_class` and
  `ultimate_parent`.
- Slicers: `instrument_type`, so the offers to supply can be taken out;
  `is_cw_reference`, which separates the legacy-system records; `segment`;
  `fiscal_year_label`.

## Files

| File | |
|---|---|
| `README.md` | This page. |
| `defence_procurement.pbix` | The model. Added when built. |
| `model_diagram.png`, `report_page.png` | Screenshots of the model view and the report page. Added when built. |
