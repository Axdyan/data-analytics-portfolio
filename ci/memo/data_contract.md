# Data contract: what each source is allowed to drift by, and why

The runner does not decide whether a moved number is acceptable. This document does, one
source at a time, and `policy.yml` is the machine-readable copy of it. The rule underneath
every entry is the same: on unchanged bytes nothing may move, and on changed bytes a figure
may move only as far as the publisher's own refresh behaviour explains. A move the publisher
cannot explain is drift outside the band, and the memo that quotes the figure needs a dated
update before the badge goes green again.

The kinds a figure can carry are `count`, `money`, `pct`, `mw`, `stat`, `ratio`, `text` and
`constant`. A band names the sign a change may take (`direction`), an absolute allowance in
percentage points for a `pct` (`points`), a relative allowance as a fraction of the committed
value (`rel`), or an absolute allowance in the figure's own unit (`abs`). A kind with no band
has no allowance: any change on a changed source is outside the band. `text` and `constant`
never have one.

## Fingerprints, and what counts as a change

A source is fingerprinted after the notebook has run, from what the notebook itself
recorded, so the runner and the notebook can never disagree about what was pulled.

| Source | Fingerprint | Read from |
|---|---|---|
| Olist, cosmetics | byte size of every CSV | the data folder after the Kaggle download |
| CanadaBuys | sha256 of the one CSV | `03-defence-procurement/memo/pull_manifest.json`, written by the notebook's pull cell |
| USWTDB current | sha256 of the API response | `04-wind-repowering/memo/pull_manifest.json` |
| USWTDB 2018 archive | sha256 of the zip | the data folder |
| EIA-923, 2013 to 2025 | sha256 of each yearly zip | the data folder |
| IESO demand and zonal | sha256 of each yearly CSV | `06-ontario-demand-forecast/memo/pull_manifest.json`, one entry per file |

The committed fingerprints live beside each manifest in `<project>.fingerprints.json`,
written by `--record-fingerprints` from the project folder as it stood when the memo's
figures were measured. They are re-recorded whenever a notebook is re-run by hand and its
memo rewritten, in the same commit.

Byte sizes rather than hashes for the Kaggle sets is a deliberate weakness: a hash of two
and a half gigabytes of CSV costs a minute the run does not need to spend on datasets whose
publishers have not touched them in years, and a changed dataset version changes the sizes.
For the same reason the workflow keeps the two Kaggle folders between runs, keyed on the
committed fingerprint file, so the download happens once per pinned version; the size
check still runs on every run, and every other source is re-pulled by its notebook.

## Olist Brazilian E-Commerce (project 01)

Kaggle, `olistbr/brazilian-ecommerce`, nine CSVs, last modified by the publisher in 2021.
Policy `static_dataset`: no change is expected and no band is given. A different byte size
means a different dataset version was downloaded, which is a reason to pin the version in
the manifest, not to accept a new number. Every figure in the memo is a count, a share or a
rank over these files, and on the same files every one must come back exactly.

## Cosmetics shop clickstream (project 02)

Kaggle, `mkechinov/ecommerce-events-history-in-cosmetics-shop`, five monthly CSVs, last
modified by the publisher in 2020. Policy `static_dataset`, same reasoning as Olist. The
memo's own caveat carries over: the price column's currency is undocumented, and the
contract cannot say more than the memo does.

## CanadaBuys contract award history (project 03)

One CSV from the publisher's open data endpoint, every PSPC award and amendment since June
2023. The publisher states a monthly refresh; the Tier 2 review observed a weekly one, six
hundred and sixteen rows in one week, and the six pulls between 2026-09-03 and 2026-09-04
returned the same hash. Policy `canadabuys_history`, `change_expected: true`.

What a refresh does: appends award and amendment rows, and occasionally restates a column
across the file, as the spring 2026 restructuring did when it added the instrument type and
amendment type columns. What it should not do: remove rows, change a contract's keyed
value, or change the meaning of a column without a note.

| Kind | Band | Why |
|---|---|---|
| count | up only | Rows, contracts, amended contracts and suppliers grow with the file. A count that falls means rows were removed, which the publisher does not do, so it is reported. |
| money | up only | Keyed value grows as awards arrive. Naive and keyed sums, subset values and segment values all move up; a fall is reported. |
| pct | 5 points | Shares of value and count move as the mix of new awards moves. Five points is wider than one month of awards has moved any share in the reviewed history, and narrower than the definitional gaps the memo is about (a reading A to reading B gap of 37 points at the narrow end). |
| stat | 10% relative | The HHI and concentration statistics move with the top suppliers' shares; a tenth of the committed value is one large award. |
| ratio | 10% relative | Same reasoning. |
| mw, text, constant | none | Not used, or never allowed to move. |

The notebook's own blocking rules are part of the contract. A9 stops the build when a
country value appears that the crosswalk does not cover; A1, A2 and A6 stop it on
duplicate keys, load rejections and a negative value. The report names the rule, and the
fix is a crosswalk row or a decision, not a band.

Fixed dates inside the memo, such as the award years 2023 to 2026 in the dual-coding
table, are counts under the same bands: rows written `Canada` in 2023 cannot grow, since
the publisher's migration to `CA` is complete, and a change there would be outside the
band for the up-only direction if it fell, which is what the contract wants to hear about.

## US Wind Turbine Database, current release (project 04)

The USGS API, `energy.usgs.gov/api/uswtdb/v1/turbines`, served as CSV, reissued several
times a year with a changelog. Policy `uswtdb_current`, `change_expected: true`.

What a reissue does: adds turbines, updates retrofit flags and years, corrects coordinates
and capacities, and reissues repowered turbines under new ids, which the memo documents as
the reason the project id and not the turbine id bridges to the 2018 release. What it can
also do, and did on 1,529 turbines, is rewrite the build year to the repowering year with
no flag, which the notebook's rule B5 measures on every run.

| Kind | Band | Why |
|---|---|---|
| count | up only | Turbines, retrofitted turbines, rewritten build years and plants in scope grow between releases. |
| pct | 5 points | The bridging percentages and the capacity shares move as turbines are added and reissued. |
| mw | 5% relative | Plant capacities move as turbines are added or corrected. |
| stat | 10% relative | The estimates and their intervals move when the panel gains a treated plant or a control; a tenth of the headline is about five points of uplift, well inside the memo's own interval. |
| ratio | 10% relative | Capacity factors, on the same reasoning. |
| money, text, constant | none | Not used, or never allowed to move. |

The estimates depend on this source and on the generation files together, so a moved
estimate is classified against every changed source's band and passes if any of them
allows it.

## US Wind Turbine Database, April 2018 archive (project 04)

One zip with a fixed catalogue entry on ScienceBase. Policy `archived_release`,
`change_expected: false`, no bands. It is the pre-repowering rotor and capacity record, and
if its bytes change the rotor comparison rests on a different file, which is a change to
read by hand, not to band.

## EIA-923 generation archives, 2013 to 2024 (project 04)

Thirteen yearly zips from the EIA archive path. The final revision of each year is
published the autumn after the year closes and is not reissued after that. Policy
`eia923_closed_years`, `change_expected: false`, no bands: if one of these files changes,
every downstream figure is drift outside the band and the report says which file moved.

The 2024 archive is treated as closed because its final revision has been published. If a
later run shows it moving, the right response is to move it into the provisional policy in
the manifest, not to widen a band.

## EIA-923 generation archive, 2025 (project 04)

The latest archive is provisional and is reissued until its final revision. Policy
`eia923_provisional_year`, `change_expected: true`. The only figures that read it are the
plant-year and plant counts over the whole fact table and the counts of plants filing in
2025: `count` may move in either direction without bound, since the provisional release
gains plants as they file and can lose rows on revision. The study estimates do not read
2025 at all, and they should not move with this file; if they do, something other than
this file moved.

## IESO hourly demand and zonal demand, closed years (project 06)

Yearly CSVs from the IESO public reports server, 2002 to 2025 for demand and 2003 to 2025
for zonal demand. A year's file is stamped once after the year closes and reissued rarely.
Policy `ieso_closed_years`, `change_expected: false`.

The training years and the first year of the test window sit in these files, so a reissue
can move every scored figure. The bands say how far a reissue of one closed year may move a
figure before it is worth a dated sentence:

| Kind | Band | Why |
|---|---|---|
| count | any direction | Hours, days and gaps in a reissued year can move either way. |
| pct | 1 point | Coverage, skill and MAPE move by tenths of a point when a few hours in a training year are corrected. |
| mw | 2% relative | Error statistics and interval widths in megawatts, on the same reasoning. |
| stat | 5% relative | Test statistics and coefficients. |
| ratio | 5% relative | Band ratios. |
| text, constant | none | Dates and design inputs never move. |

## IESO hourly demand and zonal demand, current year (project 06)

The 2026 files are rewritten every morning with the previous day's hours, so their hashes
change on every run. Policy `ieso_current_year`, `change_expected: true`.

The test window closes on 2026-08-31, inside this file, so every scored figure reads it. A
rewrite that only appends days past the window leaves them all unchanged, and the report
says so, figure by figure, as "unchanged although a source moved". A revision of an hour
inside the window moves them, and the bands are the closed-year bands: 1 point, 2%, 5%. Two
kinds of figure are allowed to grow: whole-series counts, which gain a day every morning,
and the running 2026 base-period figures, which the memo dates. The 2026 yearly mean is
the one figure the memo quotes that will drift with the calendar by construction; the
manifest says so in its note, and when it leaves the band the memo sentence is stale and
should be dated.

Seen once, on 2026-09-07: the morning rewrite appended one day to both 2026 files, six
whole-series and running-period figures moved inside their bands (the demand series from
213,456 to 213,480 hours, the 2026 mean from 17,086 to 17,080 MW, the base period from 129
to 130 days), and all 248 scored figures that read the file held exactly.

## StatCan CIMT trade data (project 05, excluded)

Project 05 is in build in a parallel session and not committed. Its backfill is eight
StatCan CIMT packages, about three gigabytes of zips covering 1988 to 2026, which does not
fit a scheduled runner's disk, time or good manners toward a public server. It is excluded
in `policy.yml` with that reason, and every summary prints the exclusion. When it ships,
the likely route is a cached Parquet artifact keyed on the notebook's own run log, so the
weekly run re-measures the figures without re-pulling the archive, and a monthly job pulls
the archive fresh.

## What the contract cannot see

- A publisher who changes the meaning of a column without changing the shape. The notebooks'
  own rules catch shape; meaning is a reading job.
- A change in the notebook's code that changes a figure on unchanged bytes. That is exactly
  what the run fails on, and it is the point: the failure is the signal to rewrite the memo
  or revert the code.
- Whether a figure inside its band is still the right sentence. The band is a threshold for
  a dated update, not a licence to leave the memo alone.
