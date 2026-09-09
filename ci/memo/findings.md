# Findings: what the first fresh-pull runs said about the five shipped projects

Measured on 2026-09-07 by running every shipped notebook top to bottom on a scratch copy of
the repository with no DuckDB file, no data folder and no pull manifest of its own, then
re-measuring every figure the project's README and findings memo quote. The manifests list
917 figures across the five projects. The reports are in `ci/reports/`, one per project,
and every number below is printed in one of them.

## The one-paragraph version

Every headline number in the portfolio comes back on a fresh pull. On the morning runs all
five sources were byte-identical to the pulls the memos were written from, so every figure
was held to an exact match at the memo's precision, and 866 of the 917 came back exactly.
The 51 that did not are all declared: 9 are design constants and notebook properties, and
42 are the uncertainty statements of the wind-repowering memo, which the committed notebook
no longer prints: two clean runs on identical bytes agree with each other on every one of
them and disagree with the memo, while every point estimate beside them holds. Nothing
failed. By the afternoon the IESO had rewritten its two 2026 files with one more day, and
the re-run that became the committed baseline exercised the drift regime for the first
time: six whole-series figures moved inside their bands and the 248 scored figures that
read the same file held exactly. On the way, the manifests caught one notebook that could
not run top to bottom on a clean checkout, a handful of memo sentences the tables do not
support as written, and five figures that had been rounded twice.

## The runs

The committed reports are the afternoon runs. The morning runs, on byte-identical sources,
gave the same figures for every project except 06, where the six figures below had not yet
moved.

| Project | Sources on this pull | Notebook | Listed | Reproduced | Drift inside band | Not reproducible |
|---|---|---|---|---:|---:|---:|
| 01 Seller risk | Olist downloaded from Kaggle in 4 s, nine files at the committed sizes | 20 cells, 7.6 s | 56 | 56 | 0 | 0 |
| 02 Funnel and retention | five monthly CSVs at the committed sizes | 25 cells, 15.5 s | 22 | 22 | 0 | 0 |
| 03 Defence procurement | CanadaBuys file re-pulled, same SHA-256 as 2026-09-04 | 77 cells, 7.8 s | 337 | 334 | 0 | 3 |
| 04 Wind repowering | USGS API, the 2018 archive and thirteen EIA-923 archives re-pulled, all at the committed hashes | 87 cells, 424 s, after a fix (below) | 220 | 173 | 0 | 47 |
| 06 Ontario demand | 49 IESO files re-pulled; the two 2026 files rewritten since the memo's pull, the 47 closed years identical | 40 cells, 84 s | 282 | 275 | 6 | 1 |

## Finding 1. The repowering notebook did not run on a clean checkout

Cell 26 of `04_load_explore.ipynb` downloads two EIA-923 archives from the publisher's
current-year path to check their workbook layout, and cell 27 opens them. The publisher
answers that path for past years with its section landing page at HTTP 200, which the
notebook goes on to discover and guard against in cells 28 to 32. On the original run cell
27 had been executed against real archives left from an earlier attempt, so its stored
output listed workbook members while cell 26's stored output showed two 56 KB downloads. On
the first fresh run cell 27 raised `BadZipFile` after 268 seconds and the remaining 60 cells
never ran.

The fix is in this commit: cell 27 checks for the zip signature and reports a file that is
not an archive by size instead of opening it, which is what the notebook's own narrative in
cell 28 already assumed had happened. No number changes. The rest of the notebook then ran
in 424 seconds, 249 of them in cell 25, whose fourteen HEAD requests the publisher answers
slowly.

## Finding 2. The repowering memo's uncertainty statements are not what the committed notebook prints

On identical bytes, every point estimate in the wind-repowering memo reproduced: the
headline +48.4%, the naive regression's +30.4%, every cohort effect, every event-time
effect, every sensitivity, the decomposition weights, the design standard error and the
minimum detectable effect computed from control variance. Thirty-four figures did not, and
they are all the same figure in different clothes: the standard error of the headline
(memo 0.042, the run 0.043), every interval bound built from a bootstrap standard error
(the headline's +36.6% to +61.2% came back +36.3% to +61.4%; the four-plant rotor class's
+114.6% to +315.2% came back +35.7% to +556.7%), the pre-trend Wald test (memo 5.06 on 3
degrees of freedom, p = 0.167; the run 3.94, p = 0.268), and the after-the-fact minimum
detectable effect (12.5% against 12.9%).

It is not randomness. The 999-draw cluster bootstrap is seeded, `np.random.default_rng(20260904)`,
the panel is fetched in plant order, and two clean top-to-bottom runs on the same bytes
agreed with each other on all 34 figures to the printed precision. The executed notebook
prints a standard error of 0.043, a Wald statistic of 3.94 and p = 0.268 in the very cell
whose stored output in the committed file says 0.042, 5.06 and 0.167. So the memo's figures,
and the notebook's own stored outputs for those cells, come from a state of the notebook or
its inputs that a clean run no longer reaches, most likely those cells were last run before
a later edit to the panel or the estimator, which the point estimates hide because they do
not depend on the draw while the bootstrap does. Which edit it was cannot be recovered from
the repository. The conclusions do not change, the intervals overlap almost entirely and the
placebo test still passes, but the numbers are not the numbers in the memo.

The manifest declares these 42 figures not reproducible, with the reason, and keeps their
queries so every report prints what that run gave beside what the memo prints. The route to
green is a hand run of the notebook top to bottom and a re-measured memo; that is the
project owner's edit, not this one's, because it rewrites 42 published figures including the
interval in the root README and the profile.

## Finding 3. Sentences the tables do not support as written

The manifest exercise reads every quoted figure back from a table, and a few sentences did
not survive that. Each manifest entry checks what the table holds and carries a note naming
the discrepancy; the memos themselves are unchanged in this commit.

- **06, the zero-zone hours.** The memo and README say three hours on 2016-05-29 have every
  zone at zero. The notebook printed the three largest published differences, all on that
  date, and the memo read the display as a count. The table holds 11 such hours on
  2016-05-29 and 24 more on 2016-10-31.
- **06, the blackout comparison.** "2,270 MW at hour 17 against 21,894 a week before" pairs
  hour 17's demand with hour 18's week-before value. Hour 17 a week before read 22,380.
- **06, the 2026 mean.** "17,086 MW over the first eight months of 2026" is the yearly
  table's 2026 row, which at the pull held 5,953 hours to 6 September. January to August
  alone averages 17,067 MW, and the row grows every morning.
- **03, a truncation.** "$10,889.4M" of legacy defence value is the two legacy rows of the
  notebook's table, which sum to 10,889.46 and round to 10,889.5.
- **04, the rebuilds.** "Two have their build year rewritten to the repowering year": the
  export table flags three of the four, plants 55265, 56160 and 56270.
- **04, two interval bounds.** "+36.6% to +61.2%": the upper bound is 61.1 whether it is
  taken from the exact bound or from the printed three decimals. "Minus 14.7% to +0.9%" on
  the repowering year: the lower bound is minus 0.147 in logs, which is minus 13.7% as
  generation. Both are moot until the bootstrap is seeded, and both are noted in the manifest.
- **04, the 2017 and 2018 cohorts.** "36% for 2017 and 2018": the table gives 36.4 and 36.6.
- **02, the view-to-cart leak.** The README says two-thirds of viewing sessions never cart
  and the memo says close to three in four; the table says 77.0%.

## Finding 4. Five figures were rounded twice

The demand-forecast notebook prints its score, coverage and peak tables at one decimal, and
the memo rounded the printed value a second time: 791.5 became 792, 1,051.5 became 1,052,
7,256.5 became 7,257, 2,581.5 became 2,582 and 645.5 became 646 (the last also in the README
and the profile). Each is half a unit from the table at the memo's precision, which an exact
check reports as a failure for a reason that has nothing to do with the data. The manifest
checks the one-decimal table value and the entry's note records what the memo prints.

Two more habits of the 04 memo needed a rule rather than a correction. Its interval bounds
were derived sometimes from the three-decimal log table the notebook prints and sometimes
from the exact bound, so the last digit depends on the route; those entries carried a
tolerance of one tenth of a point before the bootstrap finding made them moot. And its
decomposition weights are printed as fractions (0.9626) and quoted as percentages (96.3%),
which the manifest handles with a scale.

## Finding 5. The drift regime, exercised the same afternoon

Between the morning runs and the afternoon re-run the IESO rewrote `PUB_Demand_2026.csv`
and `PUB_DemandZonal_2026.csv` with one more day, as the contract says it does every
morning. The runner saw both hashes move, held the 47 closed-year files unchanged, and
classified the demand-forecast manifest under the current-year policy. Six figures moved,
all of them whole-series or running-period figures that the contract allows to grow:

| Figure | Memo | This run | Band |
|---|---:|---:|---|
| hours in the demand series | 213,456 | 213,480 | count, up only |
| hours in the zonal series | 204,695 | 204,719 | count, up only |
| zonal rows where the zones do not sum to the total | 72,152 | 72,169 | count, up only |
| zonal rows where the published difference disagrees | 29,814 | 29,815 | count, up only |
| mean 2026 demand, the yearly table's growing row | 17,086 MW | 17,080 MW | mw, 2% |
| days in the 2026-27 base period so far | 129 | 130 | count, up only |

The other 248 figures that read the current-year file, every score, interval, peak and
margin inside the fixed test window, came back exactly and are reported as "unchanged
although a source moved". That is the contract's central claim about this source, that a
rewrite which only appends days past the window leaves the scored figures alone, seen once
on real bytes. The closed-year, CanadaBuys, USGS and EIA refreshes have not yet been seen.

## What reproduced without comment

Everything else. The two Kaggle projects came back figure for figure, including the ranked
worst-ten sellers and the cohort retention table. The procurement project came back on 334
of 337 figures, including the naive and keyed sums to the cent, the sensitivity table to two
decimals, both top-fifteen supplier tables, the segment shares, the concentration statistics
and all 25 assertion counts; the three declared figures are the notebook's cell count, the
source's byte size (which the fingerprint step reads instead) and the six hand pulls the
memo recorded. The demand-forecast project came back on 281 of 282, including the full
score table, the Diebold-Mariano statistics, every coverage and reliability figure, the
hottest day hour by hour, the base-period margins and the coefficient table, which is read
from the notebook's printed output; the one declared figure is the cell count.

## What this cannot tell you

- **Whether a figure is right.** It says the memo and the notebook agree, and that the
  agreement survived a re-pull.
- **What most changed sources will do.** Only the IESO current-year rewrite has been seen
  (Finding 5). A reissued closed year, a CanadaBuys monthly refresh, a USGS release or a
  revised EIA archive have not, and the contract's bands for them are judgement until they
  are.
- **A network failure that survives two attempts.** A read timeout in the repowering
  notebook's first API call happened once in four attempts during the dry runs. The runner
  now executes a notebook a second time when the stopping exception is a network one, and
  the report says so; a failure on both attempts still reads as a stop on unchanged bytes
  and the run goes red, and a rerun by dispatch is the answer.
- **Anything about project 05**, which is excluded while its backfill is three gigabytes.

## What the project owner should do next

1. Add repository secrets `KAGGLE_USERNAME` and `KAGGLE_KEY`, then push; the first
   workflow run publishes the badge.
2. Run the repowering notebook by hand top to bottom, re-measure the 42 uncertainty
   figures in the memo, the README and the profile from that run, and drop the
   `not_reproducible` lines from those manifest entries; the seeded bootstrap then
   reproduces on every run, as the two clean runs here already did against each other.
3. Correct the sentences in Finding 3, each a few words, and update the matching manifest
   entries in the same commit.

## Closed on 2026-09-09

Items 2 and 3 above were done on 2026-09-09. The repowering notebook was run by hand top to
bottom on a re-pull of every source that came back byte-identical to the committed
fingerprints, and the 42 uncertainty figures in its memo were re-measured from that run with
the manifest's own queries: the headline interval now reads +36.3% to +61.4%, the standard
error 0.043, the pre-trend Wald test 3.94 on 3 degrees of freedom with p = 0.268, and the
after-the-fact minimum detectable effect 12.9%. The `not_reproducible` lines came off those
42 entries, so the manifest now checks 215 of its 220 figures and declares only the five
design constants. The eight sentences in Finding 3 were corrected in their memos and READMEs
and their manifest entries updated with them; the zero-zone count gained two entries, one per
day, so the demand-forecast manifest lists 284 figures and the five manifests 919. The
double-rounded figures in Finding 4 stay as they were, since the manifest already checks the
one-decimal table value behind each. Item 1 had been done earlier the same day.
