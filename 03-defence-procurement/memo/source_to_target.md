# Source to target

One row per column in the staging table: the raw header it came from, what was
done to it, the assertion that guards it, and where it is used. The raw table
holds all 91 columns as text. The staging table holds the 25 below plus the
derived columns at the bottom, and is exactly as tall as the raw table (21,890
rows, checked on every run).

Every raw header is bilingual and hyphenated. The rename map in the notebook is
the only place they appear; everything downstream reads the short name.

## Mapped columns

| Staging column | Raw header | Type | Transform | Guarded by | Used in |
| --- | --- | --- | --- | --- | --- |
| `reference_number` | `referenceNumber-numeroReference` | VARCHAR | none | A1 unique with amendment_number; A26 legacy format | Contract key; dedup partition; `is_cw_reference` |
| `amendment_number` | `amendmentNumber-numeroModification` | VARCHAR | kept as text; see `amendment_no_int` | A1; A3 non-numeric codes | Dedup ordering; amendment fact |
| `amendment_type` | `amendmentType-typeModification-eng` | VARCHAR | none | A25 contracts with no Original row | `has_original_row`; amendment fact; reading split by original row |
| `amendment_date_raw` | `amendmentDate-dateModification` | VARCHAR | none; see `amendment_date` | | |
| `instrument_type` | `instrumentType-typeInstrument-eng` | VARCHAR | none | A24 offers | Instrument sensitivity; both facts; Power BI slicer |
| `award_date_raw` | `contractAwardDate-dateAttributionContrat` | VARCHAR | none; see `award_date` | A4 cast check | |
| `contract_value_raw` | `totalContractValue-valeurTotaleContrat` | VARCHAR | none; see `contract_value_cad` | A4 | |
| `contract_amount_raw` | `contractAmount-montantContrat` | VARCHAR | none; see `contract_amount_cad` | | |
| `currency` | `contractCurrency-contratMonnaie` | VARCHAR | none | A18 not CAD, 0 rows | Scope check only |
| `supplier_legal_name` | `supplierLegalName-nomLegalFournisseur-eng` | VARCHAR | none; see `supplier_name_key` | A23 null or blank | Name key; supplier dimension; name groups |
| `supplier_standardized_name` | `supplierStandardizedName-nomNormaliseFournisseur-eng` | VARCHAR | none | A16 sparse | Not used |
| `supplier_country_raw` | `supplierAddressCountry-fournisseurAdressePays-eng` | VARCHAR | blank normalised to `(blank)`; resolved through `country_crosswalk.csv`; N/A borrowed by rule | A9 coverage BLOCK; A10 literal N/A | `country_iso2`, `country_rule`; reading A |
| `supplier_province` | `supplierAddressProvince-fournisseurAdresseProvince-eng` | VARCHAR | none | | Typed, not analysed |
| `supplier_city` | `supplierAddressCity-fournisseurAdresseVille-eng` | VARCHAR | none | | Typed, not analysed |
| `contracting_entity` | `contractingEntityName-nomEntitContractante-eng` | VARCHAR | none; the raw header carries the source's own typo | A11 not PSPC, 0 rows | Scope check only |
| `end_user_entity` | `endUserEntitiesName-nomEntitesUtilisateurFinal-eng` | VARCHAR | blank normalised to `(blank)`; substring test for DND and DRDC | A12 lookup of defence strings | `dim_end_user`, `is_dnd`; both facts |
| `unspsc_code` | `unspsc` | VARCHAR | starred, newline-separated list; first code taken as primary through the `unspsc_codes` macro | A13 null; A22 several codes | `dim_unspsc`; segments |
| `unspsc_description` | `unspscDescription-eng` | VARCHAR | first description, stars stripped | | Segment crosswalk labels |
| `gsin_code` | `gsin-nibs` | VARCHAR | none | A14 sparse | Not used |
| `title_en` | `title-titre-eng` | VARCHAR | none | | Keyword search, kept because it fails |
| `description_en` | `tenderDescription-descriptionAppelOffres-eng` | VARCHAR | none | | Keyword search, kept because it fails |
| `pct_goods_by_country` | `percentageOfGoodsByCountry-pourcentageDeBiensParPays` | VARCHAR | none | A15 empty on every row | Reading C, not computable |
| `procurement_method` | `procurementMethod-methodeApprovisionnement-eng` | VARCHAR | none | | Typed, not analysed |
| `contract_start_raw` | `contractStartDate-contratDateDebut` | VARCHAR | none | | Typed, not analysed |
| `contract_end_raw` | `contractEndDate-dateFinContrat` | VARCHAR | none | | Typed, not analysed |

## Derived in staging

| Staging column | Derived from | Type | Transform | Guarded by | Used in |
| --- | --- | --- | --- | --- | --- |
| `row_id` | row order at load | BIGINT | `row_number() OVER ()` | Staging row count equals raw row count | Traceability; join key to the country view; dedup tie-break |
| `award_date` | `award_date_raw` | DATE | `TRY_CAST` | A4 non-empty raw with null cast, 0 rows; A17 outside window, 0; A20 null, 305 | Date dimension key; date-based cuts |
| `amendment_date` | `amendment_date_raw` | DATE | `TRY_CAST` | | Amendment fact |
| `contract_value_cad` | `contract_value_raw` | DECIMAL(18,2) | thousands separators removed, `TRY_CAST` | A4; A5 zero; A6 negative BLOCK; A7 above $100M; A8; A21 constant within contract | Every value figure |
| `contract_amount_cad` | `contract_amount_raw` | DECIMAL(18,2) | thousands separators removed, `TRY_CAST` | A25 | Per-row delta in the amendment fact only; never summed |
| `amendment_no_int` | `amendment_number` | INTEGER | `CAST` only where the text is exactly three digits, else null | A3 | |
| `amendment_sort_key` | `amendment_no_int` | INTEGER | `COALESCE(amendment_no_int, -1)`, so non-numeric codes sort first | measured both ways, 0 contracts change | Dedup ordering; LAG ordering |
| `supplier_name_key` | `supplier_legal_name` | VARCHAR | accents stripped, upper-cased, punctuation removed, trailing legal-form tokens dropped, joined; blank names keyed `(blank)` | A23 | Supplier grouping; control crosswalk key; supplier dimension |

## Derived at contract grain

Columns added when the staging rows are keyed to one row per contract in
`fct_contract`.

| Column | Transform | Guarded by |
| --- | --- | --- |
| `amendment_rows` | `COUNT(*)` over the contract partition | Sum equals 21,890 |
| `first_award_date` | `MIN(award_date)` over the partition | |
| `max_value_any_amendment` | `MAX(contract_value_cad)` over the partition | A8 |
| `has_original_row` | `BOOL_OR(amendment_type = 'Original')` over the partition, coalesced to false | A25 |
| `is_cw_reference` | reference number matches `^CW[0-9]+$` | A26 |
| `value_flag` | negative, zero, over_100m, normal | A5, A6, A7 |
| `country_iso2`, `country_rule` | joined from the resolved country view by `row_id` | A9 |
| `end_user_key`, `is_dnd` | joined from `dim_end_user` on the blank-normalised end-user string | |
| `rn` | `ROW_NUMBER()` by `amendment_sort_key DESC, row_id DESC`; the row kept is `rn = 1` | Contract count 13,296 |
