# Decisions

The calls I made while building this, written down as I made them so I am not reconstructing
the reasoning months later. Ids follow this project's decision list, so they fill in out of
order as each question actually comes up. Every number here is from my own run of the notebook
on the date shown.

## D-01 The import file and its grain

Date: 2026-09-05

**Decision.** Use the HS10 monthly file, ODPFN014, at its own grain: one row per month,
ten-digit code, partner country, province of clearance and US state. The fact table keeps that
grain. The natural key is those five columns.

**Why.** Each yearly zip carries three data files at three levels of the commodity code: two
digits, six digits and ten digits. The reclassification this project is about happens at the
tenth digit, and the two coarser files are roll-ups of the fine one, so only the HS10 file can
show it. Province is needed because the dashboard's row-level security filters on it, and state
is part of the key because United States rows are split by state while every other partner's
rows leave it blank. The note to users inside the zip describes the classification rather than
the record layout, so the layout is the header row, and it is the same header in every year's
file.

**What it costs.** Size. The seven months of 2026 alone are 3,418,311 rows, so the full span
will be well over a hundred million. The fact stays at source grain in DuckDB; the dashboard
gets an aggregate of it, not the fact itself, and that is a separate decision when it comes.

**What would reverse it.** Nothing about the grain. If a question needs the six-digit
international level, that is an aggregate of this table, not a different load.

## D-02 The dictionary: how it is read, and which copy

Date: 2026-09-05

**Decision.** Parse the HS10 dictionary as fixed width with explicit column positions, decode
it as Windows-1252, keep every field as text at the raw layer, and take the copy shipped in the
most recent zip. Keep every other zip's copy under its hash so they can be compared.

**The layout, measured rather than assumed.** 53,570 lines, every one exactly 213 characters.
The columns where every line holds a space are 10, 17, 24, 28, 111, 194, 205 and 206, and the
fields start at 0, 11, 18, 25, 29, 112, 195 and 207. That is eight fields, not the six the
handoff described: code, start month, end month, unit of measure, English description, French
description, then a ten-character file tag and a six-digit month that names the month the
snapshot was cut for. A delimited reader takes the first line as a header and misparses the
rest. Zero lines fail the pattern. The file is not UTF-8; it decodes as Windows-1252.

**Why the newest copy.** Every zip ships the dictionary as it stood when that zip was built,
so the copy inside an older zip cannot describe a code opened after it. The 2026 zip's copy is
cut for July 2026. On it: 53,570 code-periods and 42,771 distinct codes, matching the handoff;
8,631 codes with more than one period; 5,962 codes with more than one distinct English
description against the handoff's 5,924; 10,930 codes with an open period, of which 2,288
previously meant something else against the handoff's 2,280. The handoff read the copy inside
the 2023 zip, which explains the small gaps. No two periods of any code overlap, and the 999912
sentinel on an open period converts to 9999-12-31 rather than to null, so a BETWEEN works.

**The headline, confirmed on this copy.** 8485100000 reads "Ships' propellers and blades
therefor" from 198801 to 200612 and "Machines, for additive manufacturing/3D printing, by
metal deposit" from 202201, and the notebook asserts both rows rather than eyeballing them.

**What would reverse it.** The snapshot comparison in the notebook showing that the newest copy
restates a historical period in a way that touches one of this project's series. Then the
period in question is documented and the older description is carried alongside.

## D-05 The changepoint method is written by hand and named for what it is

Date: 2026-09-05

**Decision.** The search for an unknown break date will be a rolling Chow scan written in the
notebook, and it will be called that. Nothing here is called Bai-Perron unless a Bai-Perron
implementation is actually run.

**Why.** The ruptures library has no wheel for this Python version and needs a C++ compiler to
build from source, so it is not in the environment. pyarrow, dbt-core and the duckdb adapter
installed and run, so no second interpreter was set up for one optional library. The known
break at January 2022 is tested directly with a Chow test either way; the scan is the check
that the data puts the break where the tariff change says it should be.

**What would reverse it.** A compiler on the machine, or a wheel. Then ruptures runs as a
cross-check on the hand-written scan, not instead of it.

**What the scan and the tests found, 2026-09-09.** The window runs from January 2019, the
first month all seventeen donors exist, to July 2026: 36 months before the break and 55 after.
The Chow test at January 2022, log value on a trend and eleven month dummies with every
coefficient free to change, gives F of 1.46 on 13 and 65 degrees of freedom for the donor
basket, p 0.158, and 1.59 for the combined basket, p 0.110. Among the sixteen donor codes with
a positive value in every month, only two clear 0.05, 8475900000 at p 0.002 and 8477903000 at
p 0.004, both with the post-break level below the pre-break fit. The scan, the same statistic at
every month with eighteen months kept on each side, puts the donor basket's largest F at January
2025 and the combined basket's in the autumn of 2020, with January 2022 ranking 26th and 27th of
the 55 months tried. For the plastics donor 8477800000 the largest F sits at August 2021, five
months before the tariff change, with a level 35.4 percent lower after it; January 2022 ranks
25th. So the data does not put a break in the donor basket at the date the tariff change says,
and the one donor where it puts one nearby puts it a few months early, which is what a code
losing its printers over the last months of 2021 would look like. The interrupted time series is
where the sizes are: the donor basket's level shift is 1.6 percent with a Newey-West p of 0.679
and the combined basket's is 3.1 percent at p 0.425, while three donors show a negative shift
below 0.05: 8477800000 at minus 25.9 percent, 8477903000 at minus 58.6 and 8477909090 at minus
16.3, all three in the rubber and plastics machinery heading. No sup-F critical value is applied
to the scan; it locates, it does not test.

## D-07 What the backfill pulls, keeps and deletes

Date: 2026-09-05

**Decision.** Pull all thirty-nine yearly zips, 1988 to 2026. Keep the zips. Extract only the
HS10 file from each, write it to one Parquet file per year with every column as text, verify the
row count, and delete the extracted CSV. Keep one copy of each distinct dictionary snapshot
under its hash. Log every attempt to `python/run_log.csv`, which is committed.

**Why the full span.** The propeller story needs 1988 to 2006 and the carbon-fibre story needs
1998 onward, so the pre-2022 years are the point, not padding. The manifest built from the
catalogue lists exactly one import zip per year and the years are contiguous, so there is no
gap to explain.

**Why the zips stay and the CSVs go.** The zip is the file as published, and its hash in the
log is what a later re-pull is compared against. The CSV is a few hundred megabytes a year and
comes back out of the zip in a second, so keeping it buys nothing.

**Why the log has thirteen columns rather than the seven planned.** The planned seven were
year, start, finish, zip bytes, rows written, status and note. Added: the resource URL, so the
log stands without the manifest; the zip's hash and whether this run downloaded it or reused
one on disk, so a re-pull is detectable; the member name, since it changes spelling across
eras; the count of distinct months, which is what the completed-year check reads; and the hash
of the dictionary snapshot the zip shipped with, which is how the snapshots are tied back to
years.

**How it stays idempotent.** A year whose Parquet exists with a row count equal to its latest ok
row in the log is skipped. A failed attempt is logged with the error text and the script moves
on, exiting non-zero at the end. A response that is not a zip, which a publisher can send at
HTTP 200, is refused before a byte is written.

**What would reverse it.** Disk. Roughly three gigabytes of zips is the cost of the immutable
raw layer, and it is paid once.

## D-08 The fact is incremental by year, and the natural key is a test

Date: 2026-09-05

**Decision.** `fct_imports_monthly` is a dbt incremental model with the delete-and-insert
strategy keyed on year. A normal run replaces the latest year already loaded and every year
after it; a `years` variable replaces exactly the years named; a full refresh rebuilds
everything. Uniqueness of the five-column natural key is asserted by a singular test on the
built table, not enforced by a merge.

**Why.** The publisher republishes whole years, and the backfill writes whole years, so the
year is the unit of work on both sides. Re-doing the latest year on every run is what keeps
the partial current year fresh as months are added. A merge on a five-column key across a
hundred-odd million rows would cost far more than it protects against, because nothing in this
pipeline ever writes part of a year.

**What would reverse it.** The publisher revising part of a year, which the file layout does
not allow for.

**What happened on the first full build, 2026-09-06.** The fact had been created on a single
year before the backfill landed, and the next build reworked only that year, because the
incremental clause looked forward from the latest year loaded and nowhere else. The
completeness check in the notebook caught it: 3,418,311 rows in the fact against 186,229,882
staged, with every dbt test passing, since the tests on the fact only see what the fact holds.
Three changes followed. The incremental clause now also takes any year present in the source and
absent from the table, which is what a backfill of earlier years needs. That build ran as a full
refresh, so the table was made in one pass rather than through a temporary table of a hundred
and eighty million rows on a machine with sixteen gigabytes of memory and a four gigabyte cap on
DuckDB. And the natural-key test was rewritten as one aggregate per year, because a single hash
table over the whole fact would not fit under that cap. The lesson kept: a test suite that only
reads the target cannot see rows that never arrived, so a completeness check against the source
sits beside it.

**And a second thing the first full build taught, 2026-09-06.** The fact built and every test
on it passed, then the corruption mart failed in a quarter of a second with an error that had
nothing to do with its SQL: DuckDB refuses to change its temporary directory once that directory
has been used, and the adapter re-applies every profile setting on each new cursor it opens, so
the first cursor opened after a spill fails on the spill-path setting. It never showed on a
smaller run because nothing spilled. The profile now leaves the spill path at DuckDB's default,
a folder beside the database file, which git ignores. dbt also wrote no results file for that
crashed build, so the notebook's results cell now refuses a results file that was not written by
a build rather than reading the previous command's by mistake.

## D-03 The concordance is the publisher's own table, and the rule I had planned is kept only as a check

Date: 2026-09-07

**Decision.** The map across the January 2022 break is Statistics Canada's ten-digit statistical
concordance, published by the border agency as two spreadsheets: the original, and the 2022-1
amendment that carries chapters 27, 39, 42, 44, 63, 72, 73 and 85. The notebook downloads both,
reads the obsolete-to-new sheet of each and writes the pairs to `crosswalks/concordance_202201.csv`
with the source file, its hash and the pull date on every row. That file is a dbt seed, and the
concordance model joins it to the dictionary at both ends. The rule the plan called for, pair a
retired code with the new codes in its own subheading or failing that its heading, is computed
alongside as a column and used for nothing except saying how often it would have been right.

**What the dictionary says happened at the break.** 852 codes end in December 2021 and 1,355 begin
in January 2022. 424 are the same code carrying on, 332 of them with a new description; 428 codes
were retired and 931 created outright. Applied to the 428 retired codes, the subheading-then-heading
rule finds new codes in the same subheading for 134 of them, only in the same heading for 284, and
nothing at all for 10, offering 5,138 candidate pairs with no way to choose among them. For the
heading this project is about it finds nothing: no code was live under 8485 in December 2021, so
the nine 3D-printing codes have no predecessor by subheading or heading.

**What the published table says.** 2,052 pairs in the original file and 455 in the amendment,
2,507 distinct pairs across both; 852 obsolete codes and 1,355 new codes, which is every code the
dictionary closes and every code it opens, and a singular test now asserts that coverage on every
build. The mapping is mostly not one to one: 1,319 pairs sit in many-to-many groups, 906 in
splits, 112 in merges, and 170 are one to one. Of the 2,083 pairs where the code changed, 744 stay
in the heading and 463 in the subheading, 278 move within the chapter and 598 cross into another
chapter. The rule would have reached 1,207 of those pairs and missed 876, and every one of the 17
pairs that feed heading 8485 is a move across headings within chapter 84, so the rule would have
missed all of them.

**What it costs.** The concordance is a judgement the publisher made, not a measurement. It says
which codes fed each new code and nothing about how much of each. A one-to-many pair does not carry
weights, so the value under an obsolete code cannot be split among its successors from this table.

**Overrides.** None were needed: every code in the series this project measures is covered by a
published pair. If a review disagrees with a published pair, the seed row is edited and the edit is
dated here, so the file stays the single place the mapping lives.

**What would reverse it.** A weighted concordance from the publisher, which does not exist for this
break, or a review that finds a published pair wrong for one of the codes in the series.

## D-04 The donor set and the window it is measured over

Date: 2026-09-07

**Decision.** The donors are the 17 codes the published concordance maps to any of the nine codes
under heading 8485, each taken over its unbroken run of dictionary periods through the break. The
donor basket and the combined basket start in January 2019, the first month all 17 exist, which
leaves 36 months before the break and 55 after it through July 2026. Membership lives in
`crosswalks/series_definitions.csv` with the rule and source on every row.

**Why these and why 2019.** The publisher named them; I did not choose them, and D-03 says why the
mechanical alternative could not have. The 2019 start is forced by 8477800000, the machinery code
that fed the plastics printers, which opened in January 2019 when the codes before it were folded
together; its predecessors ended in December 2018 and chaining them in would need a second
concordance at that break. 8477901000 dates from 2017 and every other donor from 2012 or earlier.

**What the raw numbers said before any test was run.** The recipient basket was 49.5 million
dollars in 2022 and 116.1 million in 2025, against a donor basket of 2,266.0 million in 2021 and
2,401.0 million in 2022: the goods that moved are about two percent of the codes they came from.
Five donors fell from 2021 to 2022, led by 8477800000 at 13.7 million down, 8477909090 at 9.3 and
8477903000 at 8.5; the two largest donors rose, 8479899090 by 59.7 million and 8479891000 by 54.1.
So the donor side is dominated by goods that have nothing to do with printers, and any level shift
the statistics find there has to be read against that. The plastics donor is the one place the
move is visible to the eye, and 8485200000, the plastics printers, is 54.0 percent of the recipient
basket in 2025.

**What it costs.** Three years before the break, with 2020 inside them. Nothing before 2019 for the
donor basket, so the corruption mart, not this basket, is where the 1988 to 2006 propeller history
is measured.

**What would reverse it.** Chaining the 2019 predecessors of 8477800000 through the border
agency's 2019 concordance, which would push the window back and is the first extension I would
make if the pre-period proves too short.

## D-06 Values stay in nominal Canadian dollars

Date: 2026-09-07

**Decision.** Every value in this project is the customs value as published, in nominal Canadian
dollars. Nothing is deflated. Growth rates are nominal and are labelled as such. C13 in the
assertion suite.

**Why.** There is no price index for additive manufacturing machines, and a general import price
deflator would impose the price history of everything else on a good whose own price has been
falling. The corruption mart compares shares within a year, so it needs no deflation at all. The
growth estimates compare 2021 with 2025 and are stated as nominal, which a reader can adjust with
whatever deflator they trust.

**What would reverse it.** A machinery import price index at a grain that separates these goods.

## D-09 Carbon fibre: five windows under four labels, and a longer sheet series than the handoff said

Date: 2026-09-07

**Decision.** The carbon fibre articles series carries four regime labels over five windows, read
straight off the dictionary rows and asserted by a singular test that no window spans a change of
description. Not separately coded from January 1988 to December 1997. One clean code, 6815101000
as Carbon fibres and filaments, from January 1998 to July 2001: 43 months, 34.8 million dollars,
0.81 million a month. The same code commingled with refractory brick from August 2001 to September
2014: 158 months, 216.2 million, 1.37 million a month. Not separately coded again from October 2014
to December 2021, when 6815100000 covered every non-electrical article of graphite or carbon. Three
codes from January 2022: 55 months to July 2026, 228.4 million, 4.15 million a month. No growth rate
is quoted across any of those boundaries.

**The handoff described four regimes.** It ran the commingled window into the split and did not
name the seven years and three months in between when there was no carbon fibre code at all. The
publisher's own concordance confirms the gap: it sends the three 2022 carbon fibre codes back to
6815999000, articles of stone or other mineral substances not elsewhere specified, not to
6815100000.

**The epoxide sheet series starts in 1988, not 1998.** 3921909914, film and sheet of epoxide resin
reinforced with carbon fibres, ran from January 1998 to December 2011 as the handoff said, 10.9
million dollars over 168 months. Its predecessor 3921909014 carried the same wording from January
1988 to December 1997, 5.3 million over 120 months, so the series is kept as one with two codes.
From January 2012 the sheet falls into a code shared with glass fibre, and from October 2014 into
plastics not elsewhere specified, so it ends.

**What would reverse it.** A dictionary snapshot that restates any of these periods; the snapshot
comparison in the notebook is where that would show.

## D-10 The Snowflake port is prepared for, not run

Date: 2026-09-09

**Decision.** The dbt project stays on DuckDB. The port to a Snowflake trial, last on the plan's
cut list, has not been run, and nothing in this project claims it.

**What was checked.** `dbt-snowflake` and everything it depends on resolve as wheels on this
Python, so the adapter installs without a compiler; a dry run on 2026-09-09 confirmed it. The
port needs a trial account, which does not exist yet.

**What the port would take.** The Parquet loaded through an internal stage into a raw table, the
sources rewritten from `external_location` to that table, and the DuckDB-specific SQL dispatched
by adapter: `try_strptime` and `last_day` in staging, `strftime` in the period key,
`generate_series` with `unnest` in the date dimension, `string_agg` with an `order by`, `left`,
the `filter (where ...)` aggregate clause, `make_date` in the export, and the `read_csv` calls
in the notebook's export readback. Then `dbt build` on both and the row counts of every model
reconciled table by table.

**What would reverse it.** A trial account. The row-count reconciliation is the deliverable that
would make the port claimable, and it is the only one.

## Source facts worth carrying into the data contract

Date: 2026-09-05

- **The seven older package ids on the handoff page are eight-character prefixes.** The
  catalogue's package_show call needs the full id; a title search on the catalogue returned all
  eight packages and the full ids are recorded in the notebook and the manifest.
- **Every package carries the same three files per year**: Imports, Total Exports and Domestic
  Exports. Only the imports zips are pulled.
- **The dictionary is a snapshot per zip, not one file.** Older zips carry older copies. The
  notebook parses every copy the backfill kept and compares each with the newest.
- **The dictionary's tail fields.** After the French description every line carries a file tag
  and the month the snapshot was cut for. A parser that stops at the French field folds them
  into it.
- **A missing file can come back as HTML at HTTP 200.** The fetch refuses anything whose
  content type is not zip or whose first four bytes are not the zip signature.
