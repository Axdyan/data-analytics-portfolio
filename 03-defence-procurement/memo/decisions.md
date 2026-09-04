# Decisions

Every choice in this build that a reader could reasonably have made differently,
with the measurement that settled it. Numbers come from a fresh-kernel run of
`03_load_explore.ipynb` against the source file recorded in `pull_manifest.json`.

Where a decision turned out not to matter, that is written down too. Several of
these were arguments I expected to have with the data and did not, and knowing a
choice is moot is worth as much as knowing it is load-bearing.

---

## D-01 One row per contract by keyed dedup, not DISTINCT and not MAX

`(reference_number, amendment_number)` is unique across all 21,890 rows, so the
file is one row per amendment and not one row per contract. The surviving row is
picked with `ROW_NUMBER() OVER (PARTITION BY reference_number ORDER BY
amendment_sort_key DESC, row_id DESC)` and `QUALIFY rn = 1`.

`DISTINCT` cannot work, because amendment rows differ from each other on award
date and amendment number. Every row is already distinct and nothing collapses.

`MAX(contract_value_cad)` per contract returns $66,363,740,301.42, which is
exactly what the keyed dedup returns. It agrees, but it agrees for the wrong
reason: the total is repeated unchanged on every amendment row (D-11), so the
maximum and the latest are the same number by accident of how the publisher
denormalised the file. A column that behaved the way its name suggests would
break `MAX` immediately, so it is not the rule to build on.

What the step is worth: summing every row gives $132,853,897,948.13 against a
keyed $66,363,740,301.42. The overstatement is $66,490,157,646.71, or 100.2%,
across 4,314 of 13,296 contracts.

## D-02 Non-numeric amendment codes sort first, and it does not matter

55 rows carry an amendment number that is not three digits, 54 of them `T01` and
one `S01`. `TRY_CAST` nulls them silently, so `amendment_sort_key` is
`COALESCE(amendment_no_int, -1)` and they sort before `000`.

I measured the alternative rather than arguing about it. Sorting them first and
sorting them last both return $66,356,871,765.42, and **0 contracts change**.
The decision is recorded because someone will ask, not because it moves anything.

## D-03 Contracts whose latest row is $0, and it does not matter either

A8 looks for contracts where the surviving row reports $0 while an earlier
amendment of the same contract reported more, which would mean the keyed total
quietly loses money the file actually contains. **0 rows.** Moot by measurement.

## D-04 The defence subset is DND or DRDC by substring, and it is not exclusive

No row names National Defence as the contracting entity, so the only way to
isolate defence is the end-user field. `is_dnd` is a `LIKE` across
`Department of National Defence` and `Defence Research and Development Canada`,
not an equality test, because one cell can list several bodies separated by
slashes and an exact match catches only the rows where defence appears alone.
An `IN` test on the exact string matches 374 rows against 4,229 for the substring.

**`is_dnd` means defence is among the end users, not that the contract belongs to
defence.** 759 rows name more than one body, up to 25 on a single row. The subset
overlaps other departments and is not exclusive departmental spending. The memo
has to say so, because "defence spending" is what a reader will assume it means.

Subset: 2,756 contracts, $19,878,465,949.91.

## D-05 The N/A country is resolved by rule, not by hand

`N/A` is a live value in the country field, not a null. Where the same normalised
supplier name carries exactly one real country somewhere else in the file, that
country is borrowed. Exactly one matters: a name appearing under two countries
says nothing about which one a given row belongs to.

It fires on one supplier, KNDS Deutschland to DE, recovering $654.9M. The result
goes out as `crosswalks/country_na_resolution.csv` so the borrow is something a
reader can check rather than a step buried inside a query.

## D-06 Three readings of "Canadian firm", and one of them is empty

- **Reading A, registered address.** Address resolves to CA after the dual-coding
  fix. 78.17% of defence value.
- **Reading B, Canadian-controlled.** Reading A minus Canadian-registered
  subsidiaries and joint ventures of foreign parents. Reported as a range, 24.16%
  to 41.04%, where the lower bound counts the unresearched tail as foreign and the
  upper counts it as Canadian. No point estimate, and no extrapolation from the
  researched set onto the tail.
- **Reading C, Canadian content.** The share-of-goods-by-country field is the one
  column that would answer the question the target is actually asking. It is
  **populated on 0 of 21,890 rows.** Reported as a row in the table rather than
  omitted, because the emptiness is the headline.

## D-07 The control research goes as far as 80% of value, measured not picked

Suppliers are taken in value order until the running share of Canadian-address
defence value crosses 80%, which lands at 28 suppliers on this pull. Hardcoding a
count would mean the scope silently stops meaning 80% the moment the distribution
shifts on a re-pull.

Achieved coverage is 80.06% of Canadian-address defence value, with 1,059
suppliers left outside. Everyone outside defaults to `unresolved` rather than
being quietly assumed Canadian, which is what makes reading B a range instead of
a point.

## D-08 What was cut, and why

- **A scored fuzzy-matching benchmark.** There is no entity-resolution ground
  truth in this file. The publisher's standardised name is populated on 23.2% of
  rows, and within those it is a 1:1 relabelling rather than a consolidation. A
  benchmark needs a truth set and there is not one, so the crosswalk is published
  for review instead of scored against something that does not exist.
- **GSIN as the classification field.** 8.3% populated. UNSPSC is 92.0%.
- **Keyword search for segments.** Kept in the notebook because it fails, and the
  failure is the evidence that segments cannot be defined by searching text.

## D-09 The pull sends a User-Agent

The gateway returns 403 to the default `python-requests` string and 200 to
anything else. Only that literal string is refused. The header is set explicitly
so the pull is reproducible rather than mysteriously failing for the next person
who runs it.

## D-10 The name normaliser, and what it deliberately does not split

The stop list of trailing corporate tokens is derived from the file's own trailing
tokens rather than from a generic list. It has to include `LIMITEE` and `LIMITE`:
without them the largest defence supplier in the file splits into two suppliers.
Names with no Latin characters fall back to an empty-key rule instead of
collapsing together.

**Bilingual slash-separated names are deliberately not split.** The same separator
carries genuine joint ventures, 184 names across 819 rows, so splitting on it
would invent suppliers that do not exist while merging ones that do.

## D-11 totalContractValue is denormalised to contract grain

The value column is repeated unchanged on every amendment row of a contract.
Verified two ways: A21 finds **0 contracts** carrying more than one distinct
total, and `LAG` over the total returns a delta of **0 on every one of 4,314
amended contracts**.

So the defect is a grain mismatch, not restatement. Nothing is being revised
upward over time. The same number is printed once per amendment, and summing it
double-counts. `contractAmount` is the column that varies at amendment grain, on
2,375 contracts. Award dates vary on 176.

## D-12 Crosswalk cells merge, they never overwrite

Every crosswalk is rebuilt on each run, because the source refreshes and can
introduce a value that was not there before. Rebuilding must not wipe values
already reviewed by hand, which is exactly what the first version did. A clean run
from the top blanked the country crosswalk, and the borrow rule in D-05 then
invented countries for 1,760 rows without raising anything. The file went from one
reviewed row to 1,760 fabricated ones, silently.

All four crosswalks now merge. Reviewed values win, anything new arrives blank,
and the blocking assertion refuses to let an uncovered value through unnoticed.

## D-13 Concentration is reported at two grains, and the gap is the finding

Concentration is measured once at the legal entity that signed the contract and
once at the ultimate parent behind it. Nothing about the money changes between the
two, only the question being asked.

Where research exists, the effect is real. General Dynamics was awarded under four
separate name keys worth $837.6M across 57 contracts. At entity grain it sits at
ranks 10 and 12 and never appears as a large supplier. At parent grain it is rank
5. That single consolidation moves specialized manufacturing from HHI 2,138 to
2,446, and its top-three share from 71.3% to 79.9%.

**The measured gap is a lower bound.** The parent grain can only merge what was
researched. The 1,059 suppliers outside the crosswalk each fall back to being
their own parent, so shared ownership among them is invisible by construction.
Roughly $18.8M of General Dynamics itself sits below the research cut and stays
fragmented even here. A gap of 0 on a segment means nothing was found, not that
nothing is there.

## D-14 Reading B is only read where coverage supports it

Reading B is reported only where control coverage exceeds 50%. Coverage travels
with every row of the sensitivity and segment tables and is drawn on the chart, so
a reader cannot pick up a range without also picking up how much of it was
actually researched.

It bites immediately. The `other` segment shows a reading B range of 11.9% to
74.6% on 34.8% coverage, and `uncrewed_autonomous` has 0% coverage. Neither range
means anything, and the tables now say so in a column rather than in a footnote.

## D-15 Where a contract carries several UNSPSC codes, the first is primary

The field holds up to 289 characters of codes, starred and newline separated. The
first is taken as primary. This is a real approximation, so it gets a number
rather than a shrug: **90.3% of classified defence value sits on single-code
contracts**, and the approximation only touches the remaining 9.7%.

## D-16 Family grain is sufficient, with two class-level exceptions

UNSPSC families are containers rather than categories, so tagging a whole family
to a capability risks sweeping in unrelated spend. I measured that before changing
anything. Family 7818 is **99.7%** aircraft maintenance and family 2513 is
**99.7%** aircraft, so the coarse grain costs almost nothing on both.

Two exceptions are kept, because a capability would otherwise be invisible or
misfiled:

- `251321`, the UAV class, sits inside an aircraft family. Tagged at family grain,
  the entire uncrewed capability disappears into aerospace.
- `811400`, manufacturing technologies, sits inside a research services family.

The crosswalk therefore carries family rows for all 238 families plus class rows
for the multi-class families inside the top 90% of value, 112 of them, and a class
tag overrides its family. How far down to generate class rows is derived by
running share rather than chosen.

Seven further class rows are carved to `other` because they inherit a capability
they do not belong to: truck, vessel and paint work inside the aircraft
maintenance family, and fire, sewage and tractor vehicles inside the military
vehicle family. That reassigns $37.91M.

Resulting shares of the $10,909.9M of classified defence value: aerospace 39.49%,
specialized manufacturing 16.74%, uncrewed and autonomous **0.02%**, other 43.75%.

Two things this section has to say out loud. **45.1% of defence value carries no
UNSPSC code at all**, on 260 contracts averaging $34.5M against $4.4M for
classified contracts, so the classification is missing precisely where the money
is and every segment share describes a bit over half the subset. And **uncrewed
and autonomous systems, one of the ten sovereign capabilities, is $2.1M.** There
is almost nothing here to measure.

## D-17 contractAmount has no single meaning, so it is never aggregated

Closed by measurement, and the answer is that the column cannot be used.

Of the 4,314 amended contracts, 2,168 are testable. The rest carry a null amount
somewhere or a zero total, which would make either test fail for reasons that have
nothing to do with what the column means. Partitioning those 2,168:

| Reading | Contracts | Share | Value |
| --- | ---: | ---: | ---: |
| neither | 866 | 39.9% | $11,972.5M |
| increment per amendment | 855 | 39.4% | $4,067.1M |
| both, one row carries the whole total | 353 | 16.3% | $998.0M |
| restatement of the contract | 94 | 4.3% | $88.9M |

The column is an increment on some contracts, a restatement on a handful, and
neither on the largest group, which carries **69.9% of the testable value**. No
rule reads it correctly across the file.

So no sum of amendment-to-amendment changes is reported anywhere. The per-row
delta stays in the amendment fact as a diagnostic, because it is still true row by
row, but the summed column is removed. Adding up changes in a column that means
different things on different contracts produces a number with no referent, and it
would have been a large and confident one.

This is the third structural defect in the file and the least recoverable. The
dual country coding is fixable with a crosswalk. The denormalised total is fixable
by keying. This one cannot be fixed from the published data at all, and the honest
output is a statement that the column is unusable rather than a corrected figure.

Measured again once the publisher's row type was in the staging table (A25),
most of the neither group has a mechanism. 2,686 contracts have no row typed
Original: the file holds their amendments but never recorded the award they
amend, so the amounts it does hold cannot sum to the total by construction.
Those contracts carry $10,400.0M of the $11,972.5M in the neither group. Among
the 1,568 testable contracts where the original row is present, 682 read as
increments, 568 as neither, 235 as both and 83 as restatements. So the column
is still not readable by one rule even where the file is complete, and the
decision stands. What changes is the memo's explanation: the largest share of
the unexplained value is unexplained because the file is missing the row that
would explain it, not because the publisher recorded it inconsistently.

The `LAG` chain also covers 5,498 rows rather than the 8,594 that have a prior
amendment, because the column is null often enough to break the chain on roughly a
third of them. That is why counting contracts whose amount changes gives 2,228
through the deltas and 2,375 through distinct values. The memo quotes 2,375 with
its definition stated, since that count does not depend on adjacency.

## D-18 A blank supplier name gets an explicit key, not a null

One row in the file has no supplier legal name (A23). A null legal name produced
a null name key, and every inner join on that key, in the supplier dimension,
the sensitivity mart, the segment mart and the Power BI export, dropped the row
without anything saying so. The export reconciliation caught it as one contract
fewer than the quarantine explained.

The row is CW2422761, a $0 award to National Defence with no country either. It
carries no value, so no value figure moved, but it belongs in every contract
count and had been missing from the count denominators of the sensitivity and
segment marts since they were built.

Blank names now key to `(blank)`, the same treatment blank countries and blank
end users already had. The alternative, patching the export join to match null
to null, would have left the marts one contract short and the export one
contract long. Fixing the key fixes every join at once.

## D-19 Offers to supply stay in the tables and go beside them as a line

The publisher's instrument type, added to the file in spring 2026, says that
4,239 of the 13,296 "contracts" are standing offers or supply arrangements. They
are offers to supply at a price rather than awards of money, and they carry most
of the file's $0 totals: 95.2% of supply arrangements and 65.2% of standing
offers are $0, which is 3,360 of the 3,665 zero-value contracts and the
explanation A5 was missing.

They are kept in every table rather than removed, because whether an offer is an
acquisition is a definitional call the Strategy does not make either, and this
project's job is to show what each definition does rather than to pick one. The
effect is measured in `mart_instrument_sensitivity` and reported as a line
beside the sensitivity table: on the defence subset, excluding offers moves
reading A from 78.17% to 76.42% and narrows the reading B range from 24.16 to
41.04 down to 24.31 to 37.79, on 1,897 rather than 2,280 positive-value
contracts. The offers themselves are 99.09% Canadian by address. That is a real
shift of under two points, and it is not the definitional swing the table is
about, which is why it is a line and not two more rows on the chart.

## D-20 The rename map was extended after the publisher changed the file

The rename map this build started from carried 22 columns and predates a
restructuring the publisher made between March 17 and April 10, 2026, which
added `amendmentType`, `instrumentType` and `amendmentDate`. The header cell
printed all 91 names on the first run, but the three new ones were not picked
up until the portal's supporting documentation was read against them.

They were added to the map, the staging table and both facts, and measured
before anything was built on them (A24, A25, A26). What they showed changed
three parts of the memo. The rows with no UNSPSC code, no instrument type and no
amendment type are the same 1,762 rows, none carries a CanadaBuys `CW`
reference, and every undated row is among them: they are records carried over
from the previous procurement system, and in the defence subset they are 290
contracts and 54.8% of the value, including every unclassified contract. That
gives the segment finding its mechanism. The instrument type gives A5 its
explanation and D-19 its sensitivity line. And the row type gives D-17 most of
its unexplained value back.

The lesson goes into the pitfalls file: reading the header once is not enough
against a source that refreshes. The rename map is now checked against the
live header on every run, and the data contract records the restructuring.
