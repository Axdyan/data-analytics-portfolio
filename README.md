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

## Projects

| Project | Dataset |
|---|---|
| [01: Seller Risk](01-seller-risk/) | Olist Brazilian E-Commerce |
| [02: Funnel & Retention](02-funnel-retention/) | Cosmetics Shop Clickstream |

## Repo layout

```
data_analytics_portfolio/
├── data/                    # raw data, gitignored, see each project's README for how to fetch it
├── 01-seller-risk/
├── 02-funnel-retention/
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
