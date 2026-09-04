# Findings: what repowering did to generation

Measured on the 2026-09-03 pull of the US Wind Turbine Database and the 2013 to 2025
EIA-923 generation files. Every number below has a row in `mart_estimates` or
`mart_event_study` behind it, and the notebook produces all of them top to bottom.

## The one-paragraph version

From the first full year after repowering, a repowered plant generates about 48% more
electricity than it did the year before the work, relative to never-repowered plants of the
same vintage over the same years. The 95% interval runs from 37% to 61%. The design could
have detected an uplift of 14% with 80% power, so this is not a marginal result. About nine
points of it is more nameplate capacity rather than better performance, the plants that were
repowered were already running slightly better than their controls beforehand, and four of
the 80 plants look like rebuilds rather than repowerings; drop them and the number is 43%.
Whether the rotor grew makes less difference than I expected: plants that fitted bigger
rotors gained 44%, plants that did not gained 34%, and the gap between those two is inside
the uncertainty.

## First, the trap in the source

The turbine database has a build year on every turbine. On 1,529 of the 8,480 repowered
turbines, spread across 17 plants, that column has been rewritten to the year of the
repowering, with no flag. The same column means "built in" on most rows and "rebuilt in" on
those, and a fleet-age analysis that trusts it will find a fleet younger than it is.

It matters here because build year is how I choose which never-repowered plants are fair
comparisons. Thirteen of the 17 affected plants are in the treatment group. Had I let them set
the age window, the window would have stretched to 2024 and admitted brand-new plants as
controls for twenty-year-old ones. So the window is set from the treated plants whose build
year was not rewritten, which gives 2001 to 2012, and 567 of the 1,208 never-repowered plants
fall inside it. The 13 plants stay in the treatment group; they just do not get a vote on who
they are compared with.

Two more defects worth knowing about before trusting either source. The turbine identifier
does not survive a repowering: repowered turbines are retired and reissued under new ids, so
only 10.5% of them can be found in the 2018 release by id, and for four of the nine cohort
years the figure is zero. The project id survives and bridges 92.2%, so that is the key. And
the generation publisher answers a request for a missing file with its web landing page at
HTTP 200, so a download loop that trusts the status code fills a folder with HTML.

## How the comparison is set up

This is an experiment nobody ran. The treatment is repowering, applied to a plant when every
one of its turbines was retrofitted. The treatment group is 80 plants, repowered in seven
cohorts from 2017 to 2023. The control group is 498 never-repowered plants built in the
same years as the treated ones, 2001 to 2012, each reporting a positive generation figure in
every year from 2013 to 2024. The outcome is annual net generation in logs, so an effect
reads as a percentage.

What was measured on the way in:

- **Treatment definition.** 90 plants have every turbine retrofitted, 1,208 have none, and 29
  have both. The 29 are set aside, because a plant total that is part treated and part not
  cannot be read as either. They come back in a sensitivity, counted as treated from their
  first retrofit. Of the 90, one was repowered in 2015 on its own and nine in 2024 with no
  year after treatment while the 2025 release is incomplete, so 80 enter the estimate.
- **Pre-period balance.** Indexed to 2013, mean generation for the two groups over 2013 to
  2019 runs 100, 105.9, 95.4, 101.3, 96.1, 96.2, 93.5 for treated against 100, 104.0, 96.4,
  100.3, 98.3, 96.4, 93.2 for controls. The largest gap in any year is about two index points.
  The two groups were moving together before anything was done to either.
- **Where the groups differ.** Treated plants are bigger, 135 MW against 81 MW today, and
  they were running harder before treatment: a capacity factor of 0.347 against 0.326 on
  capacity-weighted terms, 0.369 against 0.314 at the median plant, both on 2018 capacity.
  Operators repowered sites that were already doing slightly better than the comparison
  group. That is selection, it runs in the direction of overstating the effect, and it is why
  the estimate is an upper bound.
- **Capacity.** Between the 2018 release and today, treated plants went from 118.9 to 130.9
  MW, up 10.1%, while controls went from 71.8 to 72.8 MW, up 1.4%. Roughly 8.7 points of any
  generation uplift is more machine rather than better machine. This design cannot separate
  the two, and the estimate is a generation effect, not an efficiency one.

## Why this is not one A/B test, and what that changes

In a single A/B test, treatment starts on one date and every treated unit is compared with
every control over the same before-and-after window. Here treatment started in seven
different years. The obvious regression, log generation on a treated-and-after flag with a
fixed effect per plant and per year, handles that by averaging every pairwise comparison it
can find, including comparisons in which a plant repowered in 2017 serves as the control for
a plant repowered in 2021, while the 2017 plant's own effect is still building. Those
comparisons are wrong in a known direction: a control whose outcome is rising makes the
treated look worse than it is.

The regression returns 0.266, or 30.4% more generation, with a standard error of 0.027 and a
p-value of zero, and nothing about the output warns that anything is off. Taking it apart
into its 49 pairwise comparisons shows what it averaged: 96.3% of the weight sits on the seven
clean comparisons of a cohort against the never-repowered plants, 2.3% on earlier cohorts
compared with later ones while the later ones were still untouched, and 1.5% on the
comparisons that use already-repowered plants as controls. Those last ones average minus
3.3%, so they pull the number down, but they carry almost no weight, because 498
never-repowered controls swamp them. The regression is nearly right on this panel by luck of
the sample. On a panel with fewer clean controls it would not be, which is why it is reported
as the wrong answer rather than the answer.

The estimate I report avoids the problem by construction. For each cohort, I take every
plant's change in log generation from the year before that cohort's repowering to each later
year, average it over the cohort, and subtract the same average over the never-repowered
plants. Nothing that has been repowered ever serves as a control. The cohort effects are then
combined, weighted by how many plants each cohort holds. This is the estimator of Callaway and
Sant'Anna (2021), written out by hand so that every number in it can be pointed at; two
library implementations reproduce the event-time series and the cohort effects to six decimal
places.

The regression's number and mine also differ for a second reason that has nothing to do with
the estimator. The repowering year itself reads 6.7% below the year before, because the old
turbines come down before the new ones go up. Any average that includes that year for every
plant is pulled down by it. So the headline is measured from the first full year after
repowering, and the version including the transition year is reported beside it.

## The estimate

| Quantity | Log points | As generation | 95% interval |
|---|---|---|---|
| **From the first full year after repowering, the headline** | 0.395 | **+48.4%** | +36.6% to +61.2% |
| Including the repowering year | 0.289 | +33.5% | +24.0% to +43.8% |
| The repowering year alone | minus 0.069 | minus 6.7% | minus 14.7% to +0.9% |
| Naive regression, every post year averaged | 0.266 | +30.4% | +23.7% to +37.5% |

Standard errors come from redrawing plants with replacement 999 times, separately within
the treated and control groups, so that a plant's twelve years travel together. The
interval is pointwise.

**The pre-trend check.** The three placebo years before repowering, measured the same way as
the effect, come out at +3.9%, +2.3% and minus 4.5%, each inside its own interval. A joint test
that all three are zero gives a Wald statistic of 5.06 on 3 degrees of freedom, p = 0.167.
Treated and control plants were not drifting apart before treatment, which is the assumption
the whole comparison rests on. The cohort-level placebos are noisier than the aggregate: the
2020 cohort ran 12 to 17 points above its base year in 2013 to 2017, and the 2022 cohort 20
to 43 points below, which is six plants in a windy base year. The three-year base sensitivity
below is there because of that.

**Year by year after repowering.** The effect builds over the first three years and then
levels off. Each point is the average over every cohort that reaches that distance from its
repowering, so the right-hand end rests on fewer plants.

| Years since repowering | Effect | 95% interval | Cohorts, plants |
|---|---|---|---|
| +1 | +33.9% | +21.2% to +48.0% | 7, 80 |
| +2 | +46.6% | +35.0% to +59.4% | 6, 73 |
| +3 | +54.7% | +40.9% to +69.9% | 5, 67 |
| +4 | +59.4% | +44.3% to +75.9% | 4, 61 |
| +5 | +61.6% | +42.8% to +82.9% | 3, 38 |

Part of the rise is composition: the plants that reach +4 and +5 are the 2017 to 2020
cohorts, and the 2019 and 2020 cohorts show the largest effects of any (62.7% and 53.4%
against 36% for 2017 and 2018). Part of it looks real within cohort. I cannot separate the two
with seven cohorts.

**Minimum detectable effect.** Before looking at any treated plant, the question is how large
an effect 80 treated plants against 498 controls could reliably show. Taking the spread of
control plants' own changes from the year before each cohort's repowering to the years after
it, which is what a treated cohort would look like if repowering did nothing, and pooling it
across cohorts by size, the design's standard error is 0.0475. At 80% power and a two-sided
5% test that is a minimum detectable effect of 0.133 in logs, or 14.2% more generation. The
same calculation after the fact, from the bootstrap spread, gives 12.5%. The observed effect is
about three times the smallest one this design could have found, so the result does not
depend on a lucky draw. Had the effect been 10%, this study would have missed it more often
than not, and that is worth saying because 10% is a number that gets quoted for repowering.

## Does the rotor matter?

The question that started this project: is a repowering that fits longer blades a different
job from one that replaces the drivetrain and leaves the rotor alone? Rotor diameter before
the work comes from the 2018 release, bridged on the project id; after, from the current
release. A plant whose mean rotor grew by more than 2% is classed as grown. Among control
plants, which nobody repowered, only 6 of 565 show growth, so the classifier is not picking
up noise.

| Rotor class | Plants | Effect from the first full year | 95% interval |
|---|---|---|---|
| Rotor grew (median +18%) | 66 | +44.3% | +34.0% to +55.4% |
| Rotor unchanged or smaller | 10 | +34.5% | +27.9% to +41.3% |
| No 2018 record | 4 | +198.6% | +114.6% to +315.2% |

The bigger-rotor plants gained about ten points more than the others, and the two intervals
overlap. With ten plants in the second class I would not build anything on that gap. What I
can say is that the plants that did not grow the rotor still gained a third, so the uplift is
not mainly a blade story, or at least not one this data can see.

The four plants with no 2018 record are a different matter. Three of them carry no project id
at all in the current release, two have their build year rewritten to the repowering year, and
one went from 75 GWh a year to 262. Those are not repowerings in the sense of new blades on
old towers; they are rebuilds that the retrofit flag does not distinguish. They meet the
treatment definition I set before looking at any outcome, so they stay in the headline, and
the estimate without them is the first line of the sensitivity table below.

## Sensitivities

Every alternative is estimated the same way as the headline, with its own bootstrap.

| Design | Treated | Controls | Effect | 95% interval |
|---|---|---|---|---|
| Headline: balanced panel, logs, never-repowered controls in the vintage window | 80 | 498 | +48.4% | +36.6% to +61.2% |
| Drop the four plants with no 2018 turbine record | 76 | 498 | +43.0% | +33.5% to +53.3% |
| Mixed plants counted as treated from their first retrofit | 105 | 498 | +52.8% | +41.3% to +65.4% |
| Levels instead of logs, GWh per plant-year | 80 | 498 | +108 GWh, or +31.1% of the 348 GWh treated plants averaged the year before | +85 to +132 GWh |
| Controls limited to the 15 states holding a treated plant | 80 | 292 | +56.8% | +43.5% to +71.4% |
| Unbalanced panel, every plant contributes the years it has | 80 | 550 | +49.9% | +37.9% to +63.1% |
| Base is the mean of the three years before repowering | 80 | 498 | +49.6% | +40.0% to +59.9% |

Nothing moves the answer outside the headline's interval except the choice of scale. In
levels the uplift is 31% of the pre-repowering mean rather than 48%, because levels weight
every plant by its size and logs weight every plant equally, and the largest plants gained
proportionally less. Both are true; the log version is the one that answers "what does
repowering do to a plant," and the level version is closer to "what did repowering do to the
fleet's output."

The planned sensitivity that drops the plant with retrofits in more than one year was not
run, because no such plant exists in this release.

## Reading the number

The honest sentence is: repowering is associated with roughly 40 to 50 percent more annual
generation from the first full year after the work, of which roughly nine points is added
nameplate capacity and an unknown further part is selection of sites that were already
performing well. If the capacity component is stripped out on the crude arithmetic of
1.484 divided by 1.087, what remains is about 37%, and that is still an upper bound on the
performance gain.

## What this cannot tell you

- **Anything about blade material.** The turbine database has 28 fields and none of them
  records material, fibre or construction. Manufacturer and model are the nearest thing, and
  they are an inference. This is a wind asset lifecycle study, not a carbon-fibre study.
- **A causal effect free of selection.** Operators repower the sites they expect to gain the
  most from. The pre-trend check passed and the groups were balanced on trend, but they were
  not balanced on level, and the estimate is an upper bound.
- **Efficiency as opposed to output.** A capacity-factor outcome needs capacity per plant per
  year, which neither source provides. The EIA-860 generator file would, and is a separate
  build.
- **Local wind.** Year fixed effects absorb national weather, not site weather. The
  state-restricted sensitivity is the closest this gets, and it moved the estimate up, not
  down.
- **Revenue.** Generation is not revenue. Curtailment and prices are in neither source.
- **The 2024 cohort.** Nine plants repowered in 2024 have no full year after treatment until
  the final 2025 generation release restores the 754 plants missing from the provisional one.
  The notebook re-pulls by year, so that is a re-run rather than a rewrite.
- **The 4.8% of turbines with no plant id, the 2015 cohort of one plant, and the 29 mixed
  plants** in the main estimate.

## Definitions

- **Treated plant.** Every turbine at the plant carries the retrofit flag. Cohort is the
  retrofit year; no treated plant has more than one.
- **Control plant.** No turbine retrofitted, and built between 2001 and 2012, the span of
  build years among treated plants whose build year was not rewritten.
- **Study sample.** Treated plants in the 2017 to 2023 cohorts and eligible controls, each
  reporting positive generation in all twelve years 2013 to 2024. 80 and 498.
- **Outcome.** Annual net generation in MWh from the wind rows of EIA-923, summed to the
  plant-year, in natural logs. An effect of x log points is exp(x) minus 1 as a percentage.
- **Effect for a cohort in a year.** Mean change in log generation since the year before the
  cohort's repowering, over the cohort's plants, less the same mean over control plants.
- **Headline.** Each cohort's mean effect over its years from +1 onward, weighted across
  cohorts by plant count.
- **Standard error and interval.** Spread of 999 re-estimates on plants redrawn with
  replacement within the treated and within the control group; interval is the estimate
  plus or minus 1.96 standard errors.
- **Minimum detectable effect.** The effect size that a two-sided 5% test would find 80% of
  the time given the design's standard error: 2.80 times that standard error.

## Data quality checks

The table the notebook renders as `dq_assertions`, with the count measured on this pull.
BLOCK means the build did not proceed until a decision was written; WARN is flagged and
carried; NOTE is recorded.

| id | Severity | Rule | Expected | Found | Decision |
|---|---|---|---|---|---|
| B1 | BLOCK | duplicate case_id in the current turbine pull | 0 | 0 | stop if any |
| B2 | WARN | turbine with no plant id | 3,615 | 3,615 | excluded; 2.4% of capacity |
| B3a | WARN | turbine capacity missing | about 4.3% | 3,282 | carried as null |
| B3b | WARN | rotor diameter missing | about 4.7% | 3,527 | carried as null |
| B3c | WARN | build year missing | about 1.5% | 1,125 | carried as null |
| B4 | BLOCK | retrofitted turbine with no retrofit year | 0 | 0 | stop if any |
| B5 | WARN | build year rewritten to the retrofit year | 1,529 | 1,529 | 17 plants; do not set the vintage window |
| B6 | BLOCK | plant holding both retrofitted and untouched turbines | 29 | 29 | set aside; sensitivity counts them as treated |
| B7 | WARN | treated plant with retrofits in more than one year | 0 | 0 | none exist |
| B8 | BLOCK | generation years missing after the rename map | 0 | 0 | loader stops and names the year |
| B9 | WARN | plant-year with net generation at or below zero | measure | 170 | kept in levels, null in logs, fails the balance test |
| B10 | WARN | plant in the panel without twelve positive years | 53 | 53 | balanced set primary; unbalanced as sensitivity |
| B11 | WARN | plant in scope with no generation record | 18 | 18 | excluded; 1 treated, 17 controls |
| B12 | NOTE | plant-year built from more than one wind row | 11 | 11 | summed |
| B13 | WARN | treated plant outside the 2017 to 2023 cohorts | 10 | 10 | dropped: 2015 is one plant, 2024 has no post year |
| B14 | NOTE | plants filing in the provisional 2025 release | 624 | 624 | 2025 out of the panel; 1,348 filed in 2024 |
| B15 | WARN | treated plant in the study with no 2018 rotor record | 4 | 4 | reported separately, dropped in a sensitivity |
| B16 | WARN | generation row with a dot for the year | 19 | 19 | quarantined |
| B17 | NOTE | monthly columns disagree with the annual total by over 1 MWh | 0 | 0 | annual column used |
