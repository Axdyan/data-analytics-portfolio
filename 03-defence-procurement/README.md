# 03: Defence Procurement Intelligence

**Status:** Notebook, crosswalks and memos complete on the 2026-09-03 pull. Power BI model next.

**Data:** CanadaBuys contract history (`data/canadabuys/`), every PSPC contract award and amendment published since June 2023, 21,890 rows and 91 columns, refreshed monthly by the publisher under the Open Government Licence - Canada.

**Target finding:** The Defence Industrial Strategy targets 70% of defence acquisitions going to Canadian firms. Measure what the published award data says under each defensible definition of "Canadian firm", and how far apart those readings sit.

**Key finding:** The field that would answer the question, share of goods by country of origin, is empty on every one of 21,890 rows. Two defects in the file each move the headline before any definition is applied: summing the value column double-counts every amended contract, $132.9B against a keyed $66.4B, and the country field is coded two ways, 15.4% Canadian on the literal filter against 89.1% resolved. Once both are fixed, the defence subset reads 78.2% Canadian by registered address and 24.2% to 41.0% Canadian-controlled, on the same $19.9B across 2,756 contracts. The target is met or missed depending on which definition you pick, and the Strategy does not publish one. Full writeup in [`memo/findings.md`](memo/findings.md).

**Stages:**
- [x] Pull the file and record what was pulled
- [x] Load into DuckDB, stage, run the data quality checks
- [x] Fix the two defects that move the headline number
- [x] Build the crosswalks and the definition sensitivity table
- [x] Segments, charts, findings memo
- [ ] Power BI model

## What is here

| Path | What it is |
|---|---|
| `03_load_explore.ipynb` | Every query, in order, from the pull to the Power BI export. 77 cells, 25 data quality rules, two charts. |
| `definition_sensitivity.png` | Chart 1. One row per scope and measure, reading A as a point, reading B as a range, the 70% line through both. |
| `top_suppliers_by_control.png` | Chart 2. The top Canadian-address defence suppliers counted twice, at the legal entity that signed and at the parent behind it. |
| `crosswalks/` | Five published mappings, each rebuilt on every run by merge so a reviewed value is never overwritten. |
| `memo/findings.md` | The writeup: the empty field, the defects, the sensitivity table, the suppliers, the spend analysis, definitions, limits, the assertion suite. |
| `memo/decisions.md` | Twenty decisions a reader could have made differently, each with the measurement that settled it. |
| `memo/pitfalls.md` | Sixteen places where the obvious code returns a plausible wrong number against this file, ten of them silently. |
| `memo/data_contract.md` | Source, licence, both pulls with hashes, the publisher's spring 2026 restructuring, known defects tied to rules. |
| `memo/source_to_target.md` | Every staging column: raw header, transform, guarding assertion, where it is used. |
| `memo/pull_manifest.json` | What the last pull returned: URL, time, `Last-Modified`, bytes, sha256. |
| `powerbi/README.md` | The star schema, its relationships, the DAX measures and the row-level security role. |

## Method in one paragraph

The file loads as text into DuckDB, is staged with chosen types, and is checked by 25 assertions before anything is built on it; four of them block the notebook. One row per contract is produced by a keyed dedup, `ROW_NUMBER()` over the contract partition ordered by amendment, rather than by `DISTINCT` or `MAX`, and the memo shows what each alternative would have returned. Country, supplier ownership and UNSPSC segment are each resolved through a committed CSV crosswalk with a rule, a source and a confidence grade per row, and an assertion proves every raw value is covered. Three readings of "Canadian firm" are measured on two scopes and two measures, with the share of value whose ownership was actually researched carried on every row so a range is only read where it means something. Spend analysis follows: segment shares by UNSPSC, and supplier concentration at two grains, legal entity and ultimate parent, where the gap between the two is the finding.

## Crosswalks

| File | Rows | What it holds |
|---|---:|---|
| `country_crosswalk.csv` | 49 | Every raw country value to an ISO code, with the rule that mapped it. |
| `country_na_resolution.csv` | 1 | The one `N/A` row whose supplier appears under exactly one real country elsewhere, and the country borrowed. |
| `supplier_control_crosswalk.csv` | 28 | The suppliers covering 80% of Canadian-address defence value, each with ultimate parent, parent country, control class, source URL, check date and confidence. |
| `supplier_name_groups.csv` | 303 | Every name key that absorbed more than one legal-name spelling, written out so the grouping can be read. |
| `unspsc_segment_crosswalk.csv` | 350 | UNSPSC prefixes present in the defence subset, 238 families and 112 classes, tagged to a capability segment. |

## Reproduce

Set up the environment from the root README, then open `03_load_explore.ipynb` and run it top to bottom. The first cell downloads the 57.7 MB source into `data/canadabuys/` and writes the pull manifest; the notebook creates `canadabuys.duckdb` beside itself. Both are gitignored. The crosswalks in `crosswalks/` are read back in, so the reviewed values travel with the repo, and the Power BI export lands under `data/canadabuys/powerbi_export/`. The publisher refreshes the file monthly, so a later pull may return a different hash; the expected count written into every assertion is what will say what changed.

## Charts

![Definition sensitivity](definition_sensitivity.png)

![Top suppliers by control](top_suppliers_by_control.png)

## Power BI

The notebook exports a star schema, five dimensions and two fact tables sharing them, reconciled row for row against its source tables on every run. The model, its relationships, the DAX measures and the row-level security role are documented in [`powerbi/README.md`](powerbi/README.md). The `.pbix` and its screenshots follow when the model is built.
