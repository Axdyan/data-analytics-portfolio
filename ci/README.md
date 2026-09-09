# Reproducibility CI

Every number the shipped projects quote, re-run on a fresh pull of their sources.

The five project READMEs and findings memos quote several hundred figures between them. Each was printed by a notebook cell on the day the memo was written, and nothing in the repo said whether they would come back the same on a clean checkout, a new machine, or a source the publisher had since refreshed. This folder is the answer: a manifest per project listing every quoted figure with the query that reads it back from the tables the notebook builds, a runner that executes the notebook top to bottom and re-measures every listed figure, a drift contract that says how far each kind of figure may move when the source bytes change, and a workflow that does all of it on a schedule and on every push and writes a badge into the root README.

## How a run works

1. **Sources the notebook cannot fetch for itself** are fetched first. The Olist and cosmetics datasets come from Kaggle through the command line client, using `KAGGLE_USERNAME` and `KAGGLE_KEY`. The other three notebooks pull their own sources.
2. **The notebook runs top to bottom** in its own folder, headless, cell by cell, with each cell's wall time logged. That re-pulls the data, rebuilds the DuckDB file, rewrites the crosswalks, the charts and the pull manifest. A notebook that stops is reported with the cell position, the cell's opening words and the exception; when the exception is one of the notebook's own assertion rules, the report names the rule.
3. **The source is fingerprinted** after the run: the hashes the notebook itself wrote into its pull manifest, or the hashes or byte sizes of the files it downloaded, against the fingerprint recorded when the memo's figures were measured. Each source comes back unchanged, changed or missing.
4. **Every listed figure is re-measured** with its query against the rebuilt tables, or with a regular expression against the notebook's printed output where the figure is computed in Python and never written to a table.
5. **Each figure is classified.** Same bytes: it must match exactly at the precision the memo prints it, or it is a failure. Changed bytes: a moved figure is drift, inside or outside the band the policy gives its kind. Figures declared not reproducible in CI are listed with the reason.
6. **A report is written** per project, dated, in Markdown and JSON, with the verdict, the source table, the notebook's slowest cells, every figure with expected and measured values, and what the run rewrote in the working tree. The aggregate step writes `summary.md` and `badge.json`.

The run fails when any figure differs on unchanged bytes, or when a notebook stops on unchanged bytes. Drift never fails a run; it is reported so the memo can be given a dated update.

## What is here

| Path | What it is |
|---|---|
| `reproduce.py` | The runner. One file, no framework, standard library plus DuckDB, PyYAML, nbformat and nbclient. |
| `policy.yml` | The drift contract, machine-readable: one policy per source refresh behaviour, one band per kind of figure. The reasons are in `memo/data_contract.md`. |
| `manifests/<project>.yml` | Every figure the project's README and findings memo quote, with its query. |
| `manifests/<project>.fingerprints.json` | The source fingerprints the committed figures were measured on, written by `--record-fingerprints`. |
| `reports/` | The dated reports from the local dry run that shipped with this folder. Later runs publish to the `ci-reports` branch. |
| `requirements-ci.txt` | What the five notebooks import, pinned to the root `requirements.txt`, plus the runner's own needs. |
| `memo/findings.md` | What the first full runs found, including the memo sentences the manifests could not reproduce as written. |
| `memo/decisions.md` | The design choices and what would reverse each. |
| `memo/data_contract.md` | Each source, how it refreshes, how it is fingerprinted, what it is allowed to drift by and why. |
| `../.github/workflows/reproduce.yml` | The workflow: one job per project, a publish job that writes the summary, the badge and the dated reports to the `ci-reports` branch. |

## A manifest entry

```yaml
  - id: score_day_model
    quote: "Day ahead, 1 to 24: model 523 MW"
    where: [README, findings]
    kind: mw
    query: SELECT "linear model MAE" FROM mart_score WHERE leads = 'day ahead, lead 1 to 24'
    expected: 523
    sources: [ieso_demand_closed, ieso_demand_current]
```

`id` names the figure in the report. `quote` is the sentence fragment as the memo prints it, so a reader can find it. `where` says which documents quote it. `kind` picks the drift band: count, money, pct, mw, stat, ratio, text or constant. `query` runs read-only against the project's DuckDB file and its first column of its first row is the measured value; `print_match` is the alternative, a regular expression over the executed notebook's printed output, optionally pinned to a cell position and a capture group. `expected` is the committed value; the comparison precision is the number of decimals it carries, or `round` when the memo rounds more coarsely than the value it prints. `compare` allows `lt`, `le`, `gt` or `ge` for figures quoted as bounds. `tolerance` widens the exact comparison by an absolute amount, used only where the memo derived a figure from a rounded table. `scale` multiplies a printed value before comparison, for fractions the memo prints as percentages. `note` is carried into the report. `sources` names which fingerprints the figure depends on; an empty list means the figure depends on the notebook's code alone and must always match. `not_reproducible` replaces the query with the reason the figure cannot be checked in CI.

## Statuses

| Status | Meaning |
|---|---|
| reproduced | Matched at the memo's precision. On a changed source the note says "unchanged although a source moved". |
| drift, inside band | The source changed and the figure moved within the band its policy gives its kind. |
| drift, outside band | The source changed and the figure moved further than the band. The memo needs a dated update. |
| FAILED | The source did not change and the figure differs, or the query failed on unchanged bytes. The run fails. |
| not run | The notebook stopped before the table existed, the fingerprint could not be read, or the query failed on changed bytes. |
| not reproducible in CI | Declared in the manifest with a reason: a design constant, a property of the notebook file, a history of hand pulls. |

## Running it locally

From the repository root, in the project's virtual environment:

```powershell
# the full thing for one project: fetch, execute, fingerprint, measure, report
python ci/reproduce.py --project 06-ontario-demand-forecast

# measure against the DuckDB file already in the folder, without executing the notebook
python ci/reproduce.py --project 03-defence-procurement --no-execute

# every project, then the summary and the badge
python ci/reproduce.py --all --aggregate

# run against a scratch copy of the repo, so the working tree stays clean
python ci/reproduce.py --project 04-wind-repowering --root C:\scratch\repo_copy --out C:\scratch\reports

# after a hand run of a notebook whose memo was just rewritten: record the fingerprints the new figures were measured on
python ci/reproduce.py --project 03-defence-procurement --record-fingerprints

# validate every manifest and the policy without running anything; do this before a commit
python ci/reproduce.py --check
```

Reports land under `ci/reports/<project>/<date>.md` unless `--out` says otherwise. The exit code is 1 on a failure, 0 otherwise.

## The workflow

`reproduce.yml` runs every Monday at 06:00 UTC, on every push to `main`, and by hand with a project name (or `all`). A `plan` job lists the manifests in `ci/manifests/` and turns them into a matrix, so a new manifest is a new job with no workflow edit; one `reproduce` job per project checks out the repo, installs `requirements-ci.txt` on Python 3.14, runs `--check`, runs the runner and uploads the project's report folder as an artifact, including the executed notebook copy and the log. The two Kaggle datasets are kept between runs in the Actions cache keyed on their committed fingerprint files, since the contract says they do not change; the size check still runs every time, and every other source is re-pulled by its notebook. A notebook that stops on a network exception is executed a second time after sixty seconds before it counts as a stop. A `publish` job that runs even when a project job failed opens the `ci-reports` branch in a worktree, places this run's reports under their project folders, writes the summary and the badge from every project's latest report on the branch, and commits; `ci-reports` is an orphan branch that holds nothing else, and a one-project dispatch updates that project without narrowing the badge. The root README's badge reads `badge.json` from that branch through the shields.io endpoint. The workflow's own exit status follows the aggregate: red when any figure failed to reproduce on unchanged bytes.

Two repository secrets are needed for the Kaggle projects: `KAGGLE_USERNAME` and `KAGGLE_KEY`, from the API token on a Kaggle account page. Without them projects 01 and 02 report their notebook as not executed and every figure as not run, and the other three are unaffected.

## Adding or changing a figure

When a memo sentence changes, change its manifest entry in the same commit: the quote, the expected value, and the query if the table changed. When a notebook is re-run by hand and its memo rewritten from the new pull, run `--record-fingerprints` for that project so the committed fingerprints match the bytes the new figures came from, and commit the fingerprints file with the memo. A figure that was never written to a table and cannot be matched in the printed output goes in with `not_reproducible` and a reason, not out.

## What this cannot tell you

- Whether a figure is right. It says whether the figure the memo quotes is the figure the notebook produces on this pull, and whether that changed.
- Whether a change in a figure matters. The bands are my judgement per source, written down in the contract; a figure inside its band can still be worth a sentence.
- Anything about the one project it does not run. Project 05 is excluded by policy while its backfill is eight archive packages and three gigabytes; the exclusion and its reason are printed in every summary.
