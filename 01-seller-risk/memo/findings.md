# Seller Performance & Delivery Risk

Looked at Olist's order data to figure out which sellers on the platform are actually reliable
and which ones have a pattern of shipping late. Ended up building a simple risk ranking out of
it.

## The orders table had some contradictions

Before trusting any lateness numbers, I checked whether order status actually matched the
delivery dates. It mostly did, but not completely: 8 orders are marked "delivered" with no
delivery date on file at all, and going the other way, 6 orders marked "canceled" still have a
real delivery date logged. Looking at those 6 more closely, all of them were purchased,
delivered weeks later, then canceled after that, so they got delivered before anyone canceled
anything.

Both groups got dropped from the lateness math. The 8 delivered-but-dateless ones because
there's nothing to measure lateness against, and the 6 canceled-but-delivered ones because
they're not really relevant to a "did this arrive on time" question. That leaves 96,470 orders,
and on average they show up about 12 days before the estimated delivery date.

## Ranking sellers needed a volume cutoff first

Joined orders to sellers and rolled everything up: per seller, how many orders, how many were
late, what percent, and the average days late. First pass at sorting by late rate was almost
useless though, the worst "sellers" were all just single-order accounts where one late delivery
equals a 100% late rate.

Checked how order counts were actually spread across the 3,095 sellers: half have 7 or fewer
orders total, a quarter have 2 or fewer. So I cut the ranking down to sellers with at least 7
orders, the median, which leaves 1,514 sellers where the late rate is based on something more
than a coin flip.

## The actual pattern

Most of those 1,514 sellers are fine. Late rate clusters well under 10% for the bulk of them,
and it falls off fast after that. There's a real tail though, a small group of sellers running
late rates from 30% up to 64%, and that group looks genuinely different from everyone else
rather than just being the unlucky edge of a wide spread.

Worst 10 by late rate:

| Rank | Seller ID | Orders | Late orders | Late rate |
|-----:|-----------|-------:|------------:|----------:|
|    1 | b1b39487  |     14 |           9 |     64.3% |
|    2 | 312ba1d7  |      7 |           4 |     57.1% |
|    3 | 973f2178  |      9 |           5 |     55.6% |
|    4 | 95b29386  |      9 |           4 |     44.4% |
|    5 | 5acd070d  |      7 |           3 |     42.9% |
|    6 | 26e2c91e  |     12 |           5 |     41.7% |
|    7 | 538caafd  |      8 |           3 |     37.5% |
|    8 | c990d6cf  |      8 |           3 |     37.5% |
|    9 | cb41bfbc  |     11 |           4 |     36.4% |
|   10 | 821fb029  |     24 |           8 |     33.3% |

Full 15 and both charts are in the notebook.