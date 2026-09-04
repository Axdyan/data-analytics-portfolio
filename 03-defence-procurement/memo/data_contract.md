# Data contract

What was pulled, what it is, what is wrong with it, and what changed between
the first and last pull of the build.

## Source

| | |
| --- | --- |
| Dataset | CanadaBuys contract history, "All CanadaBuys contract history, 2023-06-01 onwards" |
| Publisher | Public Services and Procurement Canada, on behalf of federal departments and agencies |
| Endpoint | `https://canadabuys.canada.ca/opendata/pub/contractHistoryComplete-contratsOctroyesComplet.csv` |
| Portal record | `https://open.canada.ca/data/en/dataset/4fe645a1-ffcd-40c1-9385-2c771be956a4` |
| Data dictionary | `https://donnees-data.tpsgc-pwgsc.gc.ca/ba2/ac-cb/achatscanada-canadabuys-dd.xml` |
| Licence | Open Government Licence - Canada, `https://open.canada.ca/en/open-government-licence-canada` |
| Format | CSV, UTF-8, header row, 91 columns, most fields doubled into `-eng` and `-fra` |
| Grain | One row per contract amendment. `(referenceNumber, amendmentNumber)` is unique across the file (A1). |
| Coverage | Awards dated 2023-06-01 to 2026-08-27 on this pull, plus amendments to earlier contracts carried in from the previous system |
| Refresh | The portal record says monthly. The file's `Last-Modified` header on every pull was Fri, 28 Aug 2026 12:31:43 GMT. |

The gateway in front of the endpoint returns 403 to the default `python-requests`
User-Agent and 200 to any other string. The pull sets one explicitly.

## Pulls

| | First pull | Latest pull |
| --- | --- | --- |
| Pulled at (UTC) | 2026-09-03 12:04:48 | 2026-09-04 21:31:21 |
| Last-Modified header | Fri, 28 Aug 2026 12:31:43 GMT | Fri, 28 Aug 2026 12:31:43 GMT |
| Content-Length header | 57,669,819 | 57,669,819 |
| Bytes written | 57,669,819 | 57,669,819 |
| sha256 | `1d6c1725a400f51d2a00a15007359399ca5fe59717de9cba5e7be85b9315e11c` | identical |
| Rows | 21,890 | 21,890 |
| Columns | 91 | 91 |
| Rows rejected at load | 0 | 0 |

Six pulls between those two dates returned byte-identical files. The manifest of
the latest pull is `memo/pull_manifest.json`, written by the notebook at pull
time.

## What the publisher changed under the plan

The portal's supporting documentation records that "from March 17, 2026 until
April 10, 2026, the CanadaBuys contract history and CanadaBuys awards notices
datasets were restructured". Three columns were added that this project uses:
`amendmentType-typeModification`, "whether the entry corresponds to the
original contract, or a subsequent amendment or termination";
`instrumentType-typeInstrument`, "the type of contracting instrument used,
whether a contract, a contract against a supply arrangement, a standing offer,
or a task authorization based contract"; and `amendmentDate-dateModification`.
The same notes say the restructuring addressed "the unintended duplication of
previous contractAmount-montantContrat values in records associated with purely
administrative changes to a contract after January 2023" and removed duplicate
history records created by internal administrative updates.

The rename map this project started from predates that restructuring. The three
columns were found by reading the live header against the documentation rather
than trusting the map, and the map now carries 25 columns rather than 22.

## Columns used

25 of the 91 columns are read. Each is listed in `source_to_target.md` with its
raw header, the transform applied, and the assertion that guards it. The
remaining 66 are loaded as text and never referenced: the French doubles, the
contact, address and office fields, the procurement category, notice type,
selection criteria, trade agreements, regions of delivery, supplier operating
name and employee count, GSIN description, publication date, contract status,
and the contract and solicitation numbers.

## Known defects, with the rule that measures each

| Defect | Where | Rule | Handling |
| --- | --- | --- | --- |
| The total contract value is repeated unchanged on every amendment row, so summing it double-counts. The publisher defines it as cumulative "from contract award date to present". | `totalContractValue` | A21, 0 contracts vary | Keyed dedup to one row per contract |
| The amendment amount has no single meaning across contracts: increment on some, restatement on a few, neither on most of the value. | `contractAmount` | A25 | Never aggregated |
| Country is written as an ISO code on most rows and as a long name on the rest, a coding migration visible by award year. | `supplierAddressCountry` | A9, A10 | Published crosswalk, 49 raw values to 34 codes; N/A borrowed by rule |
| The Canadian content field is empty on every row. | `percentageOfGoodsByCountry` | A15, 21,890 rows | Reading C reported as not computable |
| 1,762 rows carry no UNSPSC code, no instrument type and no amendment type together, and none of them has a CanadaBuys `CW` reference. They are records carried over from the previous system. | `unspsc`, `instrumentType`, `amendmentType`, `referenceNumber` | A13, A26 | Kept; reported as the population behind the unclassified segment |
| 305 rows have no award date, all of them in the population above. | `contractAwardDate` | A20 | Kept, excluded from date-based cuts |
| 2,686 contracts have no row typed Original, so the file holds their amendments but not the award they amend. Their total includes value committed before the file's window. | `amendmentType` | A25 | Kept; stated as a scope caveat |
| 4,239 rows at contract grain are standing offers or supply arrangements, not contracts, and they carry most of the $0 totals. | `instrumentType` | A24, A5 | Kept; effect on the readings reported beside the sensitivity table |
| 55 amendment numbers are not three digits, 54 `T01` and 1 `S01`. | `amendmentNumber` | A3 | Sort first; moving them last changes 0 contracts |
| One row has a negative total. | `totalContractValue` | A6 | Quarantined out of every value figure |
| One row has no supplier name. | `supplierLegalName` | A23 | Kept under an explicit blank supplier key |
| The standardized supplier name is populated on 23.2% of rows and is a relabelling, not a consolidation, where present. | `supplierStandardizedName` | A16 | Not used; a deterministic name key and a published control crosswalk instead |
| GSIN is populated on 8.3% of rows. | `gsin` | A14 | Not used |
| One raw header carries a typo in the source itself, `nomEntitContractante` for `nomEntiteContractante`. | `contractingEntityName` | | The rename map carries the typo |
| Bilingual names joined with a slash also mark genuine joint ventures, 184 names across 819 rows. | `supplierLegalName` | | Not split |

## Fields that could answer the question and do not

- `percentageOfGoodsByCountry`: empty on every row. This is the field the 70%
  target most plausibly means.
- `supplierStandardizedName`: too sparse to serve as ground truth for supplier
  matching.
- `contractAmount`: unusable for totals; see above.

## Consumers

- `03_load_explore.ipynb` reads the CSV into DuckDB as text, stages it with
  chosen types, and builds everything else from the staging table.
- `crosswalks/*.csv` are rebuilt on every run by merge: reviewed values win,
  new values arrive blank, and a blocking assertion refuses an uncovered value.
- `data/canadabuys/powerbi_export/*.csv`, gitignored, is the star schema for the
  Power BI model, reconciled row for row against its source tables on every run.

## Closing pull

The pull of 2026-09-04 21:31:21 UTC, made by running the notebook top to bottom
after the last change to it, is the closing pull. It returned the same
57,669,819 bytes and the same sha256 as the first pull of 2026-09-03, with the
same `Last-Modified` header, 21,890 rows and 91 columns. The row delta against
the first pull is 0 and every figure in the memo reproduced to the cent.

The notebook re-pulls and rewrites `pull_manifest.json` on every full run, so
the manifest in the folder always describes the file the outputs were produced
from. If a later run returns a different hash, the header check, the row count
check and the expected counts written into every assertion are what will say so.
