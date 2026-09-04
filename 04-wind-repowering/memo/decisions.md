# Decisions

The calls I made while building this, written down as I made them so I am not
reconstructing the reasoning months later. Ids follow this project's decision list, so
they fill in out of order as each question actually comes up.

## D-01 The unit of analysis is the plant

Date: 2026-09-03

**Decision.** Estimate at the level of the generating plant, not the turbine or the project.

**Why.** Generation is only published per plant, monthly, in the EIA-923 file. There is no
turbine-level output anywhere in the public record. The turbine database can be rolled up
to a plant through its `eia_id`, and that roll-up is where the study's treatment and control
labels come from.

**What it costs.** A plant is a coarser thing than a turbine. Twenty-nine plants hold both
repowered and untouched turbines and cannot be labelled (D-02). And 3,615 turbines, 4.8%,
carry no plant id at all and never enter the study. Both are counted rather than hidden.

**What would reverse it.** Turbine-level or generator-level output becoming public. The
EIA-923 generator schedule reports at generator grain for some technologies, but wind plants
report the whole plant as one prime mover, so it does not help here.

## D-02 Plants holding both repowered and untouched turbines are neither treated nor control

Date: 2026-09-03

**Decision.** A plant counts as treated only where every one of its turbines was
retrofitted, and as a control only where none were. The 29 plants holding both are set
aside as their own group. They return in a sensitivity run, counted as treated from the
year of their first retrofit, so the effect of the choice is measured rather than
asserted.

**Why.** Generation is reported for the plant as a whole. At a plant where 39 of 355
turbines were repowered, the plant total is part treated and part untreated, and there is
no reading of that total which is honest. Calling it treated attributes the whole plant's
output to a change that touched a ninth of it. Calling it control puts genuinely treated
capacity in the comparison group. Setting it aside costs sample and keeps the comparison
interpretable, which is the better trade at this size.

**The count this produces, and a correction.** Measured on the current release: 90 treated
plants, 1,208 never treated, 29 mixed, totalling the 1,327 plants that carry a usable
plant id. An earlier profiling pass recorded 119 treated. That number counted every plant
with at least one retrofitted turbine, so it contains the 29 mixed plants; 90 plus 29 is
119 and the totals agree exactly. Nothing changed in the source, the two counts answer
different questions, and under the definition above the treatment group is 90.

This matters beyond bookkeeping. Any statement about the power of this design has to be
built on the group that actually enters the estimate. Dropping the 2015 cohort, which is a
single plant, and the 2024 cohort, which has no post-treatment year while the 2025 release
is incomplete, leaves 80 treated plants across seven cohorts. The minimum detectable
effect gets calculated on 80, and the memo says 80.

**What would reverse it.** Nothing about the definition. The count moves when the source
is re-pulled, and it moves again if the final 2025 generation release restores the 2024
cohort's post period.

## D-03 The outcome is annual net generation, and it is not efficiency

Date: 2026-09-04

**Decision.** Estimate the effect on annual net generation, in logs so the result reads as
a percentage. Do not present it as an efficiency or performance gain.

**Why the distinction is not pedantic.** Repowering adds capacity as well as replacing it.
Comparing the 2018 turbine records to the current ones for the plants in this study,
treated plants went from 72.9 to 77.3 turbines and from 118.9 to 130.9 MW, a capacity rise
of 10.1%. Control plants over the same period went from 71.8 to 72.8 MW, a rise of 1.4%.
So treated plants gained roughly 8.7 points of capacity relative to their controls, before
anything is said about how well that capacity performs.

Any uplift measured on generation therefore contains a capacity component and a
performance component, and this design cannot separate them. A plant that added a tenth of
its nameplate and generates a tenth more electricity has not become better at anything.
The honest phrasing is that repowering is associated with X% more generation, of which an
unknown part is simply more machine.

**What would fix it.** A capacity factor outcome needs capacity per plant per year, which
neither source used here provides. The turbine database gives a snapshot as it stands and
one archived snapshot from 2018, not an annual series. The annual generator file published
alongside the generation data would supply it and is a separate build.

**Pre-period balance, for the record.** On capacity measured in the same period as the
generation, treated plants ran at a capacity factor of 0.347 against 0.326 for controls,
weighted by capacity, and 0.369 against 0.314 at the median plant. Operators repowered
sites that were already performing slightly better than the comparison group, not worse.
That is selection, it runs in the direction of overstating the effect, and it is the reason
the estimate is an upper bound rather than a point of fact.

## D-04 The control pool is limited to plants of the same vintage

Date: 2026-09-03

**Decision.** A never-repowered plant is eligible as a control only if its build year falls
inside the range of build years among the treated plants. Measured on this pull that range is
2001 to 2012, and 567 of the 1,208 never-repowered plants fall inside it.

**Why.** A wind farm built in 1999 and one built in 2021 do not respond to a year of weather
the same way, and they are not at the same point in their lives. Treated plants are, by
construction, old enough to be worth repowering, so the comparison group should be too.

**How the range was set.** From treated plants whose build year was not rewritten to the
repowering year. Thirteen treated plants carry a rewritten year (the restatement trap in the
source, assertion B5), and using those to define the window would widen it with numbers that
are not build years. They stay in the treated group; they just do not set the window.

**Alternatives considered.** Matching each treated plant to its nearest controls on capacity
and vintage. Rejected for now: the balance checks show the two groups already move in
parallel before treatment (the indexed series diverge by at most about two points over
2013 to 2019), and matching would spend sample to fix a problem the data does not show.
Restricting controls to states holding a treated plant is run as a sensitivity instead.

**What would reverse it.** A pre-trend check that failed. It did not.

## D-05 The primary estimate uses the balanced panel

Date: 2026-09-04

**Decision.** The headline is estimated on plants that report a positive number in every one
of the twelve years 2013 to 2024: 88 treated and 498 controls, of which 80 treated enter the
estimate after the cohort cuts in D-02. The unbalanced panel, where a plant contributes
whichever years it has, is run as a sensitivity.

**Why.** Holding the set of plants fixed is what makes a change over time a change in
generation rather than a change in who is reporting. The balance test drops 53 of 639 plants,
almost all controls (52), and the sensitivity shows whether that mattered.

**What would reverse it.** The unbalanced sensitivity returning a materially different answer.
It returned 0.405 against 0.395 on the balanced set, inside one standard error.

## D-06 Where the pre-retrofit rotor diameter comes from

Date: 2026-09-03

The question this project asks is whether a repowering job grew the rotor, which needs
the rotor diameter a turbine had before the work and the diameter it has now. The
current release only holds the current value, so the baseline has to come from an older
release of the same database.

**Decision.** Take the baseline from the April 2018 release, and join it to the current
release at project grain on `usgs_pr_id`. Not at turbine grain on `case_id`.

**Why.** `case_id` does not survive a repowering. The published changelog states that
repowered turbines are retired and reissued as new records, and the measurement agrees.
Of the 8,480 turbines currently flagged as retrofitted, only 894 carry a `case_id` that
appears in the 2018 file, which is 10.5%. Broken out by the year of the retrofit it is
worse than that number suggests: 2018, 2019, 2022 and 2023 return zero matches, 2020
returns 3.0% and 2021 returns 1.1%. The only cohorts that match well are 2015 at 55.6%
and 2017 at 61.6%, and those are exactly the cohorts whose retrofits had already
happened before the April 2018 file was published. The join succeeds only where the old
file is no longer a before, so it is useless in both directions.

`usgs_pr_id` identifies the project rather than the turbine, and a project is not
retired when its turbines are replaced. It bridges 7,820 of the 8,480 retrofitted
turbines, 92.2%, and stays above 86% for every cohort from 2015 to 2023. The weakest is
2024 at 64.3%, which is what I would expect, since those are the projects most likely to
postdate the 2018 file.

**Alternatives considered.**

- Project name plus state as the key. Measured, and clearly worse: 41.8% on the 2017
  cohort and 54.5% on 2018, against 99.2% and 90.7% for the project id. Wind farms get
  renamed and a name is not an identifier.
- The restated commissioning year as a proxy for a full repower. This was the fallback
  if no baseline existed at all. It only covers turbines whose year was silently
  restated, so it would have been a proxy for one kind of repowering rather than a
  measurement of rotor change. Not needed now.

**What would reverse it.** Evidence that the project id is reassigned as well, or a
rotor comparison dominated by the -9999 sentinel once it is built at scale. Both get
checked before any rotor split is reported.

**Limits carried forward.** The 2018 file codes missing numbers as -9999 rather than
leaving them empty, on 5,137 rows for rotor diameter and 3,041 for capacity, so every
average over it has to exclude the sentinel explicitly. The 2018 file also has no
`eia_id`, so it cannot be joined to generation at all and is used for the rotor
comparison only.

## D-07 The estimator, and where the headline starts

Date: 2026-09-04

**Decision.** The headline estimate is a hand-written version of the cohort-by-year
comparison: for each repowering cohort, every plant's change in log generation from the year
before that cohort's repowering, averaged over the cohort, less the same average over the
never-repowered controls. Only never-repowered plants serve as controls. The cohort effects
are combined weighted by cohort size. Standard errors come from redrawing plants with
replacement, 999 times, separately within the treated and control groups. The naive
regression with plant and year fixed effects is reported beside it as the number that looks
fine and is not the estimate.

**Why hand-written.** So every number in it can be pointed at and explained line by line.
Two library implementations reproduce the event-time series and the cohort effects to six
decimal places, which is the cross-check, not the headline.

**Why the naive regression is not the estimate.** With repowering spread over seven years,
the regression averages comparisons in which a plant repowered earlier serves as the control
for one repowered later, while its own effect is still building. Decomposing the regression
on this panel shows those comparisons carry 1.5% of its weight, because 498 never-repowered
plants swamp them. So the regression is nearly right here by luck of the sample, and a
panel with fewer clean controls would not be so lucky. It is reported for that reason.

**Where the headline starts.** The repowering year itself reads 6.7% below the year before:
the old turbines come down before the new ones go up, so that year mixes months of outage
with months of new output. The headline is therefore the effect from the first full year
after repowering. The effect including the transition year is reported beside it, and both
are in the estimates table.

**What it is not.** It is not a capacity factor and not an efficiency gain (D-03). It is not
free of selection: operators repowered sites that were already running slightly better than
the comparison group, so it is an upper bound.

**What would reverse it.** A failed pre-trend check, or the transition-year dip turning out to
be something other than construction. Neither happened.

## D-08 The 2025 generation release is provisional and stays out of the panel

Date: 2026-09-03

The generation data for 2025 arrives in an archive named with a February 2026 release
date rather than the word Final, and it carries one workbook where every other year
carries three.

**Decision.** Build the plant-year fact table from all thirteen years, and exclude 2025
from the panel used for estimation. The fact table keeps it so the exclusion is a
modelling choice that can be reversed in one place, rather than a filter buried in a load
step where nobody would find it.

**Why.** 2025 returns 687 wind rows against 1,360 for 2024, and 624 reporting plants
against 1,348. I checked whether the year itself was only partly reported by counting how
many rows carry a number in each monthly column, and it is not: January through December
are populated at 663 to 687, the same gently rising shape 2024 shows. So the year is
complete for the plants that filed, and 754 plants that filed in 2024 have not filed yet.

The national total hides this rather than showing it. 2025 reports 464.39 TWh from 624
plants against 451.90 TWh from 1,348 plants in 2024, so the headline number goes up, not
down. Wind output is concentrated in large plants and those are the ones that report
monthly, so the early release carries most of the generation and about half of the fleet.
The damage is therefore at plant level, not in the total. Every one of the 754 absent
plants would enter a plant-year panel as a plant that stopped generating, and where that
plant is treated or control it would drag its own estimate down for a reason that has
nothing to do with repowering.

**Open consequence, not yet decided.** With the panel ending in 2024, the 2024 treatment
cohort has no post-treatment year at all, so it contributes nothing to the estimate. That
is 12 of the 119 treated plants. The choices are to drop that cohort, or to wait for the
final 2025 release and re-run. I would rather state the cohort is dropped and say why
than include a year I know is incomplete.

**What would reverse it.** The final 2025 revision, which should restore the missing
filers. The notebook re-pulls by year, so this is a re-run rather than a rewrite.

## Source defects worth carrying into the data contract

Date: 2026-09-03

Two things about the generation source that cost time and will cost the next person the
same time if they are not written down.

- **A missing file answers with a web page at HTTP 200.** Requesting a past year from the
  current-year folder returns the publisher's section landing page, roughly 57 KB of HTML,
  with a success status. Past years live under an archive folder. Any download here is
  checked on its content type and its first four bytes before it is written, because the
  status line proves nothing.
- **HEAD and GET disagree.** The same URL answers 503 to HEAD and 200 to GET, so probing
  availability with HEAD produces a confidently wrong map of what exists.
- **A dot is the missing-value marker.** It appears in key columns, including the year, on
  19 wind rows across the range. It is not null, so nothing catches it until a type cast
  fails somewhere downstream. Those rows are quarantined rather than dropped.
