# 01: Seller Risk Scoring

**Status:** Findings written up

**Data:** Olist Brazilian E-Commerce (`data/olist/`), about 99,441 orders across order items, sellers, reviews, and payments.

**Target finding:** Identify sellers with elevated risk of late delivery, and quantify the impact.

**Key finding:** Most sellers deliver reliably, late rate sits under 10% for the majority of the 1,514 sellers with enough order history to rank. A small tail runs late rates from 30% up to 64%, and that's where the real delivery risk concentrates. Full writeup in [`memo/findings.md`](memo/findings.md).

**Stages:**
- [x] Load CSVs into DuckDB
- [x] Explore & clean
- [x] Build seller-level risk features
- [x] Analyze & visualize
- [x] Write up findings
