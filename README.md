# Data Analytics Portfolio

Three end-to-end analytics projects built on public datasets, using DuckDB for SQL analysis and Python for transformation. Each project has its own README with methodology, findings, and how to reproduce.## Key finding so far

Seller delivery risk (Olist e-commerce data): most sellers deliver reliably, late rate sits
under 10% for the bulk of the 1,514 sellers with enough order history to rank. A small tail
runs late rates from 30% up to 64%, and that's where the real delivery risk on the platform
concentrates. Full writeup in [`01-seller-risk/memo/findings.md`](01-seller-risk/memo/findings.md).

## Projects

| Project | Dataset |
|---|---|
| [01: Seller Risk](01-seller-risk/) | Olist Brazilian E-Commerce |
| [02: Funnel & Retention](02-funnel-retention/) | Cosmetics Shop Clickstream |
| [03: SaaS Benchmark](03-saas-benchmark/) | SEC XBRL Frames API |
## Repo layout

```
data_analytics_portfolio/
├── data/                    # raw data, gitignored (see fetch_data.ps1)
├── 01-seller-risk/
├── 02-funnel-retention/
├── 03-saas-benchmark/
├── requirements.txt
└── README.md
```


## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

Then fetch the data (see each project's README for dataset-specific steps).