# Decisions

Every choice here could have gone another way. Each entry says what I chose, what the
alternative was, what settled it, and what would reverse it.

## D1. The notebooks are the pipeline

The runner executes each project's notebook top to bottom and reads the tables it
builds. The alternative was a parallel set of scripts that rebuilt the tables the CI way.
A parallel pipeline is a second implementation to keep in step with the first, and the
claim being tested is that the notebook produces the memo's numbers, not that some other
code does. Reversed if a notebook takes longer than a runner allows; the fix then is to
move the slow part into a module the notebook imports, which keeps one implementation.

## D2. Manifests read tables; they do not recompute

A manifest entry is a query against a mart, a fact table or an assertion table the
notebook wrote. Where the memo's number is arithmetic on two table figures (a share, a
gap, a difference in points), the query does that arithmetic and nothing more. The
alternative was to re-derive figures from raw tables with independent SQL, which would
test the notebook's logic rather than its reproducibility, and would have to be maintained
as a second implementation. Reversed for a project whose notebook writes no marts.

## D3. Two regimes, decided by bytes

Same source bytes: exact match at the memo's precision, or failure. Changed bytes: drift,
inside or outside a per-source band. A single global tolerance would have hidden a code
change behind a small number and flagged a publisher's routine refresh as a failure. The
fingerprint is what separates the two, and it is read from what the notebook recorded, so
the runner never has its own opinion about what was pulled. Reversed if a source turns out
to change bytes without changing content, in which case that source needs a content hash
rather than a file hash.

## D4. Fingerprints from pull manifests and file hashes, sizes for Kaggle

Three notebooks write a pull manifest with hashes; the runner reads it. The archives
project 04 downloads without a manifest are hashed by the runner. The two Kaggle datasets
are fingerprinted by byte size: two and a half gigabytes of CSV that nobody has touched
since 2020 do not justify a minute of hashing per run, and a version change changes the
sizes. Reversed if Kaggle ever reissues either dataset at the same sizes, which would show
up as a failure on "unchanged" bytes and be corrected by switching that source to hashes.

## D5. Printed output is a legitimate table

Some figures the memos quote are computed in the notebook's Python and printed, never
written to a table: a Wald statistic, a design standard error, a decomposition weight, a
row in a wide matrix. The alternative was to declare them not reproducible. Instead the
runner can match a regular expression against the executed notebook's printed output,
pinned to a cell position and a capture group. It is more fragile than a query, a changed
print format breaks it, and the report says which cell it read. Reversed per figure: any
print_match that breaks twice should become a table the notebook writes.

## D6. Interval bounds get a tenth of a point

The 04 memo derived its percentage interval bounds from the three-decimal log table the
notebook prints, and in a few rows from the exact bound, so the last digit differs by one
depending on the route. Those entries carry `tolerance: 0.1` and the manifest says why.
The alternative was to pick one route and let the other rows fail, which would have
reported a rounding habit as a reproduction failure. Reversed if the memo is rewritten to
one convention, at which point the tolerances come out.

## D7. Double-rounded memo figures are checked at the table's precision

Six figures in the 06 memo were rounded a second time from the one-decimal table the
notebook prints, so 791.5 became 792. The manifest checks the one-decimal table value and
the entry's note records what the memo prints. The alternative was to edit the memo, which
is the project's document, not the CI's. Reversed when the memo is next rewritten from a
new pull; the entries then take the new printed values.

## D8. Memo discrepancies are recorded, not corrected

The manifest exercise found sentences in the shipped memos that the tables do not support
as written: a count read from a three-row display, two figures paired from adjacent hours,
a mean labelled with a shorter window than it covers, a truncation, a two that is a three,
an interval bound off by a point. Each manifest entry checks what the table actually holds
and carries a note naming the discrepancy, and `findings.md` lists them. The alternative
was to edit five shipped memos in a CI commit. Those memos have Notion pages, profile lines
and commit history behind them, and a one-line correction each is the project owner's
call. Reversed by that call: when a memo is corrected, its manifest entry's expected value
and note change in the same commit.

## D9. Reports go to an orphan branch

The workflow commits its reports, the summary and the badge to `ci-reports`, an orphan
branch, and `main` never receives a machine commit. The alternative was to commit reports
to `main` on every run, which puts a bot's commits between the hand-written ones and makes
every push trigger a push. The first dated reports, from the local dry run, ship under
`ci/reports/` on `main` so a reader of the repo without the branch sees what a report looks
like. Reversed if GitHub's raw endpoint for the badge proves unreliable, in which case the
badge moves to a gist.

## D10. Project 05 is excluded, and says so

Its backfill is eight archive packages and three gigabytes. Pulling that weekly from a
public statistical agency's server for a portfolio badge is the wrong trade. The exclusion
is in `policy.yml` with its reason and prints in every summary. Reversed when the project
ships and a cached artifact keyed on its own run log exists; the weekly run then measures
against the cache and a monthly job refreshes it.

## D11. Bands per source, not per project

A project can read several sources with different refresh behaviours: 04 reads a live
database, a fixed archive, closed annual files and a provisional one. Each figure names
the sources it depends on, and a moved figure is classified against every changed source's
band, passing if any allows it. A per-project tolerance would have let the provisional
2025 file excuse a move in an estimate that never reads it. Reversed if the attribution
proves wrong for a figure; the fix is the figure's `sources` list.

## D12. A notebook's own blocking rule is a designed stop

When a notebook stops on one of its assertion rules, the report names the rule and the
summary says the notebook was stopped by it. On changed bytes that is the notebook doing
its job and the run does not fail; the figures downstream are not run. On unchanged bytes
it is a failure, because the same bytes cannot have changed shape. Reversed never; this
is what the rules were written for.

## D13. Weekly on Monday morning, and on every push

The schedule is early Monday UTC so the badge is fresh for the week and the publishers'
overnight rewrites are in. Every push to `main` also runs, because a memo edit is exactly
the moment its manifest should be checked. The alternative was a path filter, which would
skip the runs that matter most. Reversed if the push runs become a cost problem; the filter
then keeps notebooks, manifests, memos and READMEs.

## D14. Executed notebooks are artifacts, not commits

The runner writes an executed copy of each notebook with outputs, which is the evidence for
every print_match. It goes into the run's artifact with ninety days' retention and is
deleted before the reports are committed, because five copies a week would be a quarter of
a gigabyte a year on the branch. Reversed if a dispute about a printed value needs the
copy after ninety days; the run can be repeated by hand.

## D15. Not reproducible is a status, not an omission

A figure that cannot be checked in CI, a design constant, a count of notebook cells, a
history of hand pulls, an assertion the notebook checks at six decimals and prints at four,
goes into the manifest with `not_reproducible` and a reason. It appears in the report and
counts in the verdict line. The alternative was to leave it out, and a manifest that lists
what it cannot do is more useful to the next reader than one that looks complete.

## D16. Kaggle through the command line client and two secrets

Projects 01 and 02 read datasets that Kaggle hosts and that the notebooks assume are on
disk. The runner downloads them with the official client when the files are absent, using
`KAGGLE_USERNAME` and `KAGGLE_KEY`. Without the secrets those two projects report their
notebook as not executed and every figure as not run, and the other three are unaffected.
The alternative was to vendor the datasets, which their licences do not clearly allow.

## D17. Exit codes: failure fails, drift does not

The runner exits 1 on a figure that differs on unchanged bytes, a notebook that stops on
unchanged bytes, or a runner error; the workflow follows. Drift of any size exits 0 and
colours the badge yellow when outside its band. A red badge means the repo disagrees with
itself; a yellow one means the world moved. Reversed if a yellow badge is ignored for long
enough that it should have been red, which is a reason to shorten a band, not to change
the rule.

## D18. The static Kaggle datasets are kept between runs

The workflow caches `data/olist` and `data/cosmetics` keyed on the committed fingerprint
file, so the two Kaggle downloads, about two and a half gigabytes a week, happen once per
pinned version rather than every Monday. Every other source is re-pulled by its notebook
on every run, because re-pulling is the point. The cache does not weaken the check: the
runner still compares every file's byte size to the fingerprint on every run, and pinning
a new dataset version changes the key and forces a fresh download. Reversed if a cached
run ever reports the files as unchanged when the publisher has reissued them, which would
mean sizes are no longer a good enough fingerprint and hashes should replace them.

## D19. A network failure gets one more attempt

A read timeout in a notebook's first API call, which happened once in four attempts on
the repowering notebook, would otherwise read as the notebook stopping on unchanged
bytes and turn the run red. The runner now executes the notebook a second time, once,
after sixty seconds, when the stopping exception is a network one (a timeout, a reset, a
refused connection), and the report says so. Any other exception, a failed assertion or a
bad archive among them, is the notebook's own stop and is not retried, because a stop is
what the run exists to report. Reversed if a source starts failing routinely; the fix then
belongs in that notebook's pull cell, not in the runner.

## D20. Manifests are validated before anything runs

A typo in a kind, a policy name or a source id would otherwise pass silently as "no band"
or "no source", and a duplicated id would make a report ambiguous. The runner validates a
manifest before executing its notebook and refuses an invalid one, and `--check` runs the
same validation over every manifest and the policy without running anything, which the
workflow does first and which is cheap enough to run before every commit. Reversed never;
the check costs a second.

## D21. The badge is written from every project's latest report

The publish job puts this run's reports onto the `ci-reports` branch first and aggregates
from the branch, so a one-project dispatch updates that project's row and the badge still
counts all five. Aggregating from the run's artifacts alone would have narrowed the badge
to whatever ran. Reversed if a project is retired; its folder then comes off the branch by
hand.
