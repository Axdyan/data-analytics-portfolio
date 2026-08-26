# Data Analytics Portfolio

Three end-to-end analytics projects built on public datasets, using DuckDB for SQL analysis and Python for transformation. Each project has its own README with methodology, findings, and how to reproduce.

## Projects

| # | Project | Dataset | Status |
|---|---------|---------|--------|
| 01 | Seller Risk | Olist Brazilian E-Commerce | In progress |
| 02 | Funnel & Retention | Cosmetics Shop Clickstream | In progress |
| 03 | SaaS Benchmark | SEC XBRL Frames API | Not started |

## Repo layout

data_analytics_portfolio/
├── data/                    # raw data, gitignored (see fetch_data.ps1)
├── 01-seller-risk/
├── 02-funnel-retention/
├── 03-saas-benchmark/
├── requirements.txt
└── README.md

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Then fetch the data (see each project's README for dataset-specific steps).