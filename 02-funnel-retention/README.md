# 02 — Funnel & Retention

**Status:** Not started

**Data:** Cosmetics shop clickstream (`data/cosmetics/`) — ~20.7M events (view/cart/purchase).

**Target finding:** Conversion funnel drop-off rates and cohort retention by signup month.

**Stages:**
1. Load events into DuckDB
2. Build funnel stages (view → cart → purchase)
3. Cohort retention analysis
4. Visualize
5. Write up findings