# Data Analytics Portfolio

End-to-end analytics projects built on public datasets, using DuckDB for SQL analysis and Python for transformation and charts. Each project has its own README with the data, the method, the finding, and how to reproduce it.

## Key findings so far

**Seller delivery risk** (Olist e-commerce data): most sellers deliver reliably, late rate sits
under 10% for the bulk of the 1,514 sellers with enough order history to rank. A small tail
runs late rates from 30% up to 64%, and that's where the real delivery risk on the platform
concentrates. Full writeup in [`01-seller-risk/memo/findings.md`](01-seller-risk/memo/findings.md).

**Funnel & retention** (cosmetics shop clickstream): the real leak in the funnel sits before the
cart, not after, two-thirds of sessions that view a product never add anything to a cart, while
cart-to-purchase conversion is a comparatively gentle 1 in 6. $23.99M of $29.86M in cart value,
80.3%, is never converted, and month-1 retention falls off a cliff for every cohort but one
unexplained outlier. Full writeup in [`02-funnel-retention/memo/findings.md`](02-funnel-retention/memo/findings.md).

**Wind repowering uplift** (US Wind Turbine Database and EIA-923 generation): from the first full
year after repowering, a repowered plant generates 48% more than it did the year before the
work, relative to 498 never-repowered plants of the same vintage, with a 95% interval of 37% to
61% and a minimum detectable effect of 14%. About nine points of that is added capacity, the
estimate is an upper bound, and whether the rotor grew (44% against 34%) is inside the
uncertainty. The obvious fixed-effects regression says 30% and the memo shows why that is not
the answer. Full writeup in [`04-wind-repowering/memo/findings.md`](04-wind-repowering/memo/findings.md).

## Projects

| Project | Dataset |
|---|---|
| [01: Seller Risk](01-seller-risk/) | Olist Brazilian E-Commerce |
| [02: Funnel & Retention](02-funnel-retention/) | Cosmetics Shop Clickstream |
| [04: Wind Repowering Uplift](04-wind-repowering/) | US Wind Turbine Database, EIA-923 |

## Repo layout

```
data_analytics_portfolio/
├── data/                    # raw data, gitignored, see each project's README for how to fetch it
├── 01-seller-risk/
├── 02-funnel-retention/
├── 04-wind-repowering/
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
