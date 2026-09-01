# Funnel & Retention

Looked at five months of clickstream data from a cosmetics shop (20.7 million events, October 2019
through February 2020) to figure out where sessions actually drop out of the buying process, and
whether customers who buy once come back to buy again. Three real findings came out of it: where
the funnel actually leaks, how retention behaves cohort to cohort, and how much cart value never
converts.

## The funnel leaks before the cart, not after

94.4% of sessions include at least one view event, but only 21.7% of sessions ever add anything to
a cart. That means close to three out of every four sessions that view a product walk away without
even starting a cart. From there, cart to purchase is a much gentler slope: 21.7% down to 3.4%
overall, or about 1 in 6 carting sessions converting.

Cart abandonment is the number most e-commerce writeups focus on, but for this shop the bigger
opportunity sits earlier, in whatever makes someone look at a product and leave without
considering buying it at all.

## Retention drops sharply after the first cohort, then flattens

Checked repeat purchasing first, since it's what makes cohort retention worth doing at all: 16.0%
of the 110,518 purchasers in this data bought again in a different calendar month, a real signal to
build on.

Grouped purchasers into cohorts by the month of their first purchase and tracked how many came
back in later months. Month-1 retention for the October cohort is 18.5%, then it drops hard: 9.8%
for November, 8.5% for December, 8.9% for January. Instead of a steady decline across cohorts,
there's one sharp step down after October, then a flat floor around 8 to 10% for everyone after it.
October also holds up a little differently over time, including a small uptick at month 3 that the
other cohorts don't show. I don't have a clean explanation for why, worth digging into further if
this were a live business rather than a public dataset.

## $23.99M of $29.86M in cart value never converts

Summed price across every cart event per session, split by whether that session eventually
purchased. $23,993,092 of $29,863,849 in cart value, 80.3%, belongs to sessions that never bought
anything. Actual purchase revenue over the same period comes to $6,348,005, a bit higher than the
cart value tied to purchasing sessions, which means some purchases happen without a matching cart
event in that same session.

One caveat worth stating plainly: the source dataset doesn't document what currency the price
column is in. I'm reporting these as dollars since that's the most likely convention, not a
confirmed fact.

Full queries, both charts, and the cohort tables are in the notebook.
