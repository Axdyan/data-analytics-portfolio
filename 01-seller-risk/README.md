# 01 — Seller Risk Scoring

**Status:** Not started

**Data:** Olist Brazilian E-Commerce (`data/olist/`) — ~99,441 orders, order items, sellers, reviews, payments.

**Target finding:** Identify sellers with elevated risk of late delivery / poor reviews, and quantify the impact.

**Stages:**
1. Load CSVs into DuckDB
2. Explore & clean
3. Build seller-level risk features
4. Analyze & visualize
5. Write up findings