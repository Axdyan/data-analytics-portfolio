# Data contract

What was pulled, from where, when, and what is known to be wrong with it. Every count in
this file is measured on the pull recorded in `pull_manifest.json`, which the notebook
rewrites on every run with the byte count, SHA-256 and the publisher's own Created-at stamp
of every file. The current year's file is rewritten daily and older years have been
reissued, so any figure quoted from this project carries the pull it was measured on.

Two report families from one publisher, the Independent Electricity System Operator of
Ontario. Both are public reports on `https://reports-public.ieso.ca/public/` (the older
host `reports.ieso.ca` redirects there) and are used under the IESO's terms of use, at
`https://www.ieso.ca/en/Terms-of-Use`. The forecast is built on the first family; the
second is dashboard context and a consistency check.

## 1. Hourly Ontario and market demand

| | |
|---|---|
| Publisher | Independent Electricity System Operator (IESO), Ontario |
| Endpoint | `https://reports-public.ieso.ca/public/Demand/PUB_Demand_YYYY.csv`, one file per year from 2002; each year also appears as `PUB_Demand_YYYY_vNNN.csv` and the current year as `PUB_Demand.csv` |
| Grain | one row per hour: `Date`, `Hour` (1 to 24, the hour ending), `Market Demand`, `Ontario Demand`, in megawatts |
| Layout | three metadata lines beginning with a doubled backslash (report name, `Created at`, `For YYYY`), then the header, then data; CRLF line endings |
| Clock | a fixed standard-time clock: every one of the 8,893 complete dates carries 24 rows, including the clock-change days, so no hour is duplicated in November or skipped in March |
| Refresh | the current year's file is regenerated daily (Created-at `2026-09-06 07:30:14` on this pull); past years are stamped once at the end of January following the year (`2019-01-31` for 2018 through `2026-01-31` for 2025); years 2002 to 2017 carry a single `2018-05-22 08:00:00` stamp from a republication |
| Pulled | 2026-09-06 23:01 UTC, 25 files, 5,610,058 bytes, 213,456 data rows |
| Coverage | from 2002-05-01, the day Ontario's wholesale market opened, to 2026-09-06 hour 1 |
| Manifest | `memo/pull_manifest.json`: per file, the URL, bytes, SHA-256, Created-at stamp, the year written inside the file, whether the header matched, and the data row count |

Checks the notebook runs on every pull, with the assertion id that guards each and the count
on this pull:

- **Header drift.** Every file's header line is compared with the one read before the
  pull; a difference blocks the load (B2, 0 files). The year written in the metadata is
  compared with the year in the file name; a mismatch blocks (B3, 0 files).
- **Key.** One row per date and hour; a duplicate blocks (B1, 0). Dates before the window
  end with other than 24 rows are counted (B6, 1), every hour missing from a generated
  spine between the first and last published hour is listed (B5, 1), filled from its
  neighbours and flagged (B10, 1). A day of the test window missing from the series blocks
  (B14, 0).
- **Casts.** Every column loads as text and is cast in staging; failed casts are counted
  (B4, 0).
- **Plausibility.** Hours where market demand sits below Ontario demand are counted and
  recorded (B7, 43); hours below half of the same hour a week earlier are counted and read
  (B8, 12). That last check finds the blackout of 14 August 2003 and nothing else, and those
  hours are kept because they happened.
- **Versions.** The highest-numbered versioned copy of every year is hashed against the
  plain yearly file; years where they differ are counted (B13, 0 of 25). The plain file is
  the one loaded.

Known defects, measured on this pull:

- **A missing hour inside a complete year.** `PUB_Demand_2025.csv` carries 8,759 rows where
  a year has 8,760 hours. The day with 23 rows is 2025-05-01 and the absent hour is hour 1,
  the hour from midnight to one: hour 24 of April 30 reads 13,795 MW, hour 2 of May 1 reads
  12,352, and nothing between them. There is no marker. It is the only gap in 213,456 hours.
  Filled with the rounded mean of its neighbours, 13,074 MW, and flagged, never dropped.
- **Market demand below Ontario demand on 43 hours.** The market column, which should
  include exports and losses on top of Ontario demand, is the smaller of the two on 43 of
  213,456 hours. Recorded; the model does not read the column.
- **The current year is a moving file.** On this pull it ends at 2026-09-06 hour 1, its last
  day has one row, and its Created-at stamp is the morning of the pull. The analysis window
  therefore ends on a fixed, complete month, 2026-08-31 (D-03), and the test window is
  asserted to sit entirely inside the published data.
- **A real event that looks like an error.** From 15:00 on 2003-08-14 to 02:00 on
  2003-08-15, 12 hours read below half of the same hour a week earlier, the lowest 2,270 MW
  against 21,894. Kept; fifteen years before the earliest training window.
- **No weather, no price, no forecast of the publisher's own.** The report is actuals only.
  Nothing in it says what the operator forecast for the same hours, so no comparison with
  the operator's forecast is made here.

The series on this pull: 213,456 hours, minimum 2,270 MW, maximum 27,005 MW (2006-08-01,
hour ending 16), mean 16,251 MW. Annual mean demand ran from 17,919 MW in 2005 down to
15,053 MW in 2020 and back to 16,621 MW in 2025; the annual peak of 2025 was 24,862 MW on
2025-06-24 at hour ending 19, and the first eight months of 2026 reached 25,646 MW on
2026-07-14 at hour ending 17.

## 2. Hourly zonal demand

| | |
|---|---|
| Endpoint | `https://reports-public.ieso.ca/public/DemandZonal/PUB_DemandZonal_YYYY.csv`, one file per year from 2003, with the same versioned copies and undated current file |
| Grain | one row per hour: `Date`, `Hour`, `Ontario Demand`, ten zones (`Northwest`, `Northeast`, `Ottawa`, `East`, `Toronto`, `Essa`, `Bruce`, `Southwest`, `Niagara`, `West`), `Zone Total`, `Diff` |
| Layout and clock | as for the demand file |
| Pulled | 2026-09-06, 24 files, 15,307,326 bytes, 204,695 data rows |
| Used for | the dashboard's zonal page and its row-level-security role, from January 2024 (233,750 zone-hours exported); a consistency check on the provincial total |

Known defects, with the assertion that guards each and the count on this pull:

- **A quoted thousands separator in one column.** When the difference column reaches four
  digits it is written as `"-1,054"`. A CSV reader that sniffs the dialect reads the file
  as unquoted, splits that value on its comma, and fails the load on a row with sixteen
  fields where fifteen are expected; the first load attempt failed exactly that way on
  `PUB_DemandZonal_2013.csv` line 4534. The quote character is set explicitly, the separator
  is stripped before the cast, and the rows that carried one are counted: 129 of 204,695,
  all in the `Diff` column (B17). A value that still fails the cast blocks (B18, 0).
- **The zones do not sum to the published total.** On 72,152 rows, 35%, the ten zones add to
  a figure other than `Zone Total`. All but 4 are within 5 MW, which is rounding; the largest
  gap is 531 MW, on 2012-05-06 at hours 12 to 14 (B11).
- **The published difference is not always zone total minus Ontario demand.** On 29,814 rows,
  by at most 75 MW (B12). The zonal data is not used for anything the difference would
  affect.
- **Three hours with every zone at zero.** On 2016-05-29 at hours 12 to 14 every zone and the
  zone total read 0 while Ontario demand reads 17,799 to 18,416 MW, so the published
  difference is minus the whole province. These are the extreme rows the notebook prints;
  they sit outside the exported window.

## 3. What travels with the repo

The data files are gitignored. What is committed is the manifest, the holiday crosswalk the
notebook writes and then reads back (254 rows, 2002 to 2027), the two charts, the memos and
the notebook itself. A fresh clone rebuilds everything from the notebook: the first cells
pull every file, the manifest is rewritten, and the assertion table at the end says whether
anything moved against what was measured here.

## What changed between pulls

The notebook was run against the report server on 2026-09-05 during the build and on
2026-09-06 for the run this memo is written from. Every closed year's plain file hashed
identically on both pulls, and every table inside the analysis window printed the same
numbers. What moved was the current year's file: 5,929 rows and 152,045 bytes on the first
pull against 5,953 rows and 152,660 bytes on the second, one day of hours, with its Created-at
stamp moving from `2026-09-05 07:30:09` to `2026-09-06 07:30:14`; the zonal files gained the
same day. The two all-years zonal counts moved with it, B11 from 72,140 to 72,152 and B12
from 29,809 to 29,814. Nothing inside the test window changed, which is what the fixed
window (D-03) is for. When a closed month is revised the manifest shows it as a changed hash
on that year's file.
