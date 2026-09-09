# Data Analytics Portfolio

[![numbers reproduced](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FAxdyan%2Fdata-analytics-portfolio%2Fci-reports%2Fbadge.json)](https://github.com/Axdyan/data-analytics-portfolio/tree/ci-reports)

End-to-end analytics projects built on public datasets, using DuckDB for SQL analysis and Python for transformation and charts. Each project has its own README with the data, the method, the finding, and how to reproduce it.

## Key findings so far

**Seller delivery risk** (Olist e-commerce data): most sellers deliver reliably, late rate sits
under 10% for the bulk of the 1,514 sellers with enough order history to rank. A small tail
runs late rates from 30% up to 64%, and that's where the real delivery risk on the platform
concentrates. Full writeup in [`01-seller-risk/memo/findings.md`](01-seller-risk/memo/findings.md).

**Funnel & retention** (cosmetics shop clickstream): the real leak in the funnel sits before the
cart, not after, three in four sessions that view a product never add anything to a cart, while
cart-to-purchase conversion is a comparatively gentle 1 in 6. $23.99M of $29.86M in cart value,
80.3%, is never converted, and month-1 retention falls off a cliff for every cohort but one
unexplained outlier. Full writeup in [`02-funnel-retention/memo/findings.md`](02-funnel-retention/memo/findings.md).

**Defence procurement** (CanadaBuys contract awards): the field that would measure Canadian
content is empty on every one of 21,890 rows, so the 70% Canadian-firm target can only be read
by supplier address or by ownership. Two defects in the file move the headline before any
definition does, a value column that double-counts every amended contract and a country field
coded two ways. Fixed, the defence subset reads 78.2% Canadian by registered address and 24.2%
to 41.0% Canadian-controlled, on the same $19.9B across 2,756 contracts. The target is met or
missed depending on the definition, and the Strategy does not publish one. Full writeup in
[`03-defence-procurement/memo/findings.md`](03-defence-procurement/memo/findings.md).

**Wind repowering uplift** (US Wind Turbine Database and EIA-923 generation): from the first full
year after repowering, a repowered plant generates 48% more than it did the year before the
work, relative to 498 never-repowered plants of the same vintage, with a 95% interval of 36% to
61% and a minimum detectable effect of 14%. About nine points of that is added capacity, the
estimate is an upper bound, and whether the rotor grew (44% against 34%) is inside the
uncertainty. The obvious fixed-effects regression says 30% and the memo shows why that is not
the answer. Full writeup in [`04-wind-repowering/memo/findings.md`](04-wind-repowering/memo/findings.md).

**Additive manufacturing trade reconstruction** (Statistics Canada import files, 1988 to 2026):
Canada's ten-digit import codes change meaning, and 8485100000 meant ships' propellers from
1988 to 2006 before it meant metal 3D printers from 2022. A join on the code alone would
misdescribe 8.49% of import value across 39 years and lose another 35.24% under codes that no
longer exist, 89.13% of 1988 alone; joined on the code and the month against the dictionary's
own validity ranges, every one of 186 million rows lands on exactly one meaning. The nine
3D-printing codes rose from $49.5M in 2022 to $116.1M in 2025 with nothing before them to
compare against. The seventeen codes they came from, named by the publisher's own
concordance, are fifty times larger and show no fall at the break; the one that does, plastics
machinery, bridges the plastics printers to 142% growth from 2021 with a bootstrap interval of
36% to 1,463%, against 48% for the basket whose goods do not change. Carbon fibre has five
stretches under four regime labels and cannot be read as a series. Full writeup in
[`05-additive-trade/memo/findings.md`](05-additive-trade/memo/findings.md).

**Ontario demand forecast** (IESO hourly demand, 2002 to 2026): a day ahead, a transparent
linear model with no weather input misses hourly demand by 523 MW, 3.0% of demand, against
1,221 MW for the same-hour-last-week baseline, removing 57% of its error; a week ahead it
removes 15%, and at the last lead of the week the two cannot be told apart. Its 80% interval
covers 77.5% of hours at 1,563 MW wide against the baseline's 79.0% at 3,824 MW, and both fail
in summer. The day-ahead peak error of 646 MW is five times the 128 MW median gap between the
fifth and sixth highest daily peaks of a base period, so the forecast cannot tell a top-five
peak day from the day that just misses. Full writeup in
[`06-ontario-demand-forecast/memo/findings.md`](06-ontario-demand-forecast/memo/findings.md).

## Every number above is re-run

The badge at the top is written by a workflow that runs each shipped project's notebook top to bottom on a fresh pull of its sources, every Monday and on every push, and re-measures every figure quoted in the project's README and findings memo against the tables the notebook just rebuilt. Same source bytes must give the same number to the precision the memo prints it, or the run fails. Different bytes are publisher drift, read under a per-source contract that says how far each kind of figure may move before the memo needs a dated update. Figures that cannot be reproduced in CI are listed as such rather than dropped. The runner, the manifests, the drift contract and the memos are in [`ci/`](ci/); the dated reports and the badge live on the [`ci-reports`](https://github.com/Axdyan/data-analytics-portfolio/tree/ci-reports) branch so `main` stays hand-committed.

## Projects

| Project | Dataset |
|---|---|
| [01: Seller Risk](01-seller-risk/) | Olist Brazilian E-Commerce |
| [02: Funnel & Retention](02-funnel-retention/) | Cosmetics Shop Clickstream |
| [03: Defence Procurement](03-defence-procurement/) | CanadaBuys Contract Award History |
| [04: Wind Repowering Uplift](04-wind-repowering/) | US Wind Turbine Database, EIA-923 |
| [05: Additive Manufacturing Trade Reconstruction](05-additive-trade/) | Statistics Canada CIMT imports by HS10, 1988 to 2026 |
| [06: Ontario Demand Forecast](06-ontario-demand-forecast/) | IESO hourly Ontario demand |

## Repo layout

```
data_analytics_portfolio/
├── data/                    # raw data, gitignored, see each project's README for how to fetch it
├── 01-seller-risk/
├── 02-funnel-retention/
├── 03-defence-procurement/
├── 04-wind-repowering/
├── 05-additive-trade/       # plus dbt/ for the modelling layer, python/ for the backfill and its run log, crosswalks/ for the seeds
├── 06-ontario-demand-forecast/
├── ci/                      # the reproducibility runner, one manifest per project, the drift contract, memos
├── .github/workflows/       # the reproduce workflow that writes the badge and the dated reports
├── requirements.txt
└── README.md
```

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Then fetch the data. Each project's README has the dataset-specific steps.
