# 04: Wind Repowering Uplift

No public dataset records blade material. The turbine database used here carries 28 fields and not one of them names material, fibre or construction, so nothing in this project can tell you what a blade is made of. This is a wind asset lifecycle study written by someone who used to build blades, and the question it answers is about generation, not composites.

**Status:** Analysis complete. Dashboard in progress.

**Data:** US Wind Turbine Database pulled from the USGS API on 2026-09-03 and again, byte-identical, on 2026-09-09 (`data/uswtdb/`), 75,727 turbines carrying a retrofit flag and a retrofit year, plus the April 2018 archived release for pre-repowering rotor diameters and capacity. Joined to EIA-923 plant-level generation for 2013 to 2025 (`data/eia923/`), 14,077 plant-years across 1,486 wind plants.

**The question:** Repowering is sold as a generation uplift. Measured against never-repowered plants of the same vintage, what is the uplift, and does it differ between projects that grew the rotor and projects that only replaced the drivetrain?

**How the comparison is set up:** Repowered plants are the treatment group, 80 plants across seven cohorts from 2017 to 2023. Never-repowered plants built in the same years are the control group, 498 of them. Nobody randomised this: operators repower the sites they expect to gain the most from, so the first job is checking pre-period balance and testing whether the two groups were already drifting apart before any work happened. Retrofits landed in different years rather than all at once, which is what makes this harder than a single A/B test and why the obvious regression returns a number that looks fine and is biased. The minimum detectable effect at 80% power sits next to the estimate, so the size of uplift this design could and could not have found is on the record either way.

**Key finding:** From the first full year after repowering, a repowered plant generates 48% more than it did the year before the work, relative to its controls, with a 95% interval of 36% to 61%. The design could have detected 14%. The repowering year itself reads 7% down, because the old turbines come down before the new ones go up. About nine points of the uplift is added nameplate capacity rather than better performance, the treated plants were already running slightly better than their controls beforehand, and four of the 80 look like rebuilds; without them the figure is 43%. Whether the rotor grew matters less than expected: plants that fitted bigger rotors gained 44%, plants that did not gained 34%, and that gap is inside the uncertainty.

**The trap in the source:** On 1,529 repowered turbines the build year has been silently rewritten to the repowering year. Trusting it makes the fleet look younger than it is, and here it would have let brand-new plants into the control group for twenty-year-old ones. Details in `memo/findings.md`.

**The naive number and why it is not the estimate:** A regression with plant and year fixed effects gives 30%. Taken apart, 1.5% of its weight rests on comparisons that use already-repowered plants as controls, which is why it is nearly right on this panel and would not be on one with fewer clean controls. The estimate reported is a hand-written cohort-by-year comparison against never-repowered plants only, cross-checked against two library implementations to six decimals.

**Charts:** `event_study.png`, the effect by year since repowering with the naive regression as a reference line and the contributing cohorts printed under the axis. `bacon_decomposition.png`, the 49 pairwise comparisons inside the naive regression, by weight and estimate.

**Memo:** `memo/findings.md` for the results and what they cannot say, `memo/decisions.md` for the eight design decisions and what would reverse each, `memo/data_contract.md` for the sources and their defects, `memo/source_to_target.md` for every column read and the check that guards it.

**Power BI:** `powerbi/README.md` carries the star schema, the measures and the row-level security role. The notebook exports the four tables it is built from.

**Stages:**
- [x] Check the sources: legacy turbine releases, the yearly generation files, the libraries
- [x] Pull the turbine table, record exactly what was pulled, stage it and run the data quality checks
- [x] Load generation year by year and measure how many plants actually link
- [x] Build the plant panel, assign treatment and control, set the vintage window
- [x] Estimate the uplift, run the pre-trend check and the power calculation
- [x] Charts and findings memo
- [ ] Power BI model

**Environment:** Python 3.14, DuckDB, pandas, numpy, scipy, matplotlib; pyfixest for the naive regression; `differences` and `csdid` as cross-checks on the hand-rolled estimator.
