# 02: Funnel & Retention

**Status:** Findings written up

**Data:** Cosmetics shop clickstream (`data/cosmetics/`), about 20.7 million events across 5 months (October 2019 to February 2020).

**Target finding:** Conversion funnel drop-off rates and cohort retention by first-purchase month.

**Key finding:** The funnel's biggest leak sits before the cart, not after, two-thirds of sessions that view a product never add anything to a cart, while cart-to-purchase conversion is a comparatively gentle 1 in 6. That leaves $23.99M of $29.86M in cart value, 80.3%, unconverted, and month-1 retention falls off a cliff for every cohort except one unexplained outlier. Full writeup in [`memo/findings.md`](memo/findings.md).

**Stages:**
- [x] Load events into DuckDB
- [x] Build funnel stages (view → cart → purchase)
- [x] Cohort retention analysis
- [x] Visualize
- [x] Write up findings
