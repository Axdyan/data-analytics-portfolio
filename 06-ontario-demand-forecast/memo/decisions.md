# Decisions

The calls I made while building this, written down as I made them so I am not
reconstructing the reasoning months later. Each one says what was decided, why, what it
costs, and what would reverse it. Measurements quoted here are from the notebook's own
tables on the pull named in the data contract.

## D-01 The target is Ontario demand, not market demand

Date: 2026-09-05

**Decision.** Forecast the `Ontario Demand` column. Carry `Market Demand` into the fact
table for the dashboard and do not model it.

**Why.** Ontario demand is what the province consumes. Market demand adds exports and the
grid's own losses on top of it, so it moves with what neighbouring systems are buying,
which is a different question from how much Ontario will draw tomorrow. Every user I can
name for this forecast, an operator scheduling supply or a large consumer deciding whether
to curtail, is asking the first question.

**What it costs.** Nothing in the model. The market column is checked once, for hours
where it sits below Ontario demand, which it should never do, and the count is recorded.

**What would reverse it.** A user whose exposure is to the export flow. Then market demand
is the target and the same notebook runs on the other column.

## D-02 Forecasts are issued once a day at midnight for the next 168 hours

Date: 2026-09-05

**Decision.** Every day in the backtest is an origin at the end of hour 24. The forecast
covers the seven days after it. A day-ahead forecast is leads 1 to 24; a week-ahead forecast
is leads 145 to 168. Leads 13 to 36 are reported as well, labelled as the day-ahead bucket a
forecast issued late in the morning of the day before would actually cover.

**Why.** One origin per day is the operational shape of a demand forecast, and a midnight
origin makes the hour of day a fixed property of each lead, which is what lets one linear
model per lead carry the daily shape in its intercept. The 13 to 36 bucket is there because
nobody issues a day-ahead schedule at midnight; it is set before noon on the day before, so
the leads that schedule actually depends on start half a day later than lead 1.

**What it costs.** An hourly origin would give many more forecasts per day and a smoother
error curve. It would also multiply the compute by 24 and blur the question of which
forecast a user acts on.

**What would reverse it.** A user with an intraday decision, such as a storage dispatcher.
That is a different design, not a change to this one.

## D-03 The test window is fixed and ends on a complete month

Date: 2026-09-05

**Decision.** Score forecasts whose seven target days all fall between 2025-01-01 and
2026-08-31. The year before the window is scored too, but only to calibrate the intervals;
none of its numbers are reported. The window end is a constant in the notebook, not "the
latest date in the file".

**Why.** The current year's file is rewritten every day, so a notebook that scored up to the
last published hour would give a different answer on every run and no number in this memo
could be reproduced. Ending on the last complete month before the pull means a re-pull a
week later reproduces every figure here, and the pull manifest says which bytes did it.

**What it costs.** A few days of the most recent data are unused. When September 2026 is
complete the constant moves one month and the notebook is rerun; the memo is then re-read
against the new tables.

**Measured.** 602 test origins from 2024-12-31 to 2026-08-24, so that every one of the 168
leads is scored exactly 602 times; 372 calibration origins before them; 2,799 backtest
origins in all, the earliest 2018-12-26, which is where the first refit's five-year window
starts. On the 2026-09-06 pull the current year's file ran to hour 1 of that day, six days
past the window end.

**What would reverse it.** Nothing about the principle. The constant moves as months close.

## D-04 The baseline is the seasonal naive at one week

Date: 2026-09-05

**Decision.** The forecast every model has to beat is the demand at the same hour of the
same weekday one week earlier. A second, weaker baseline that repeats the origin day seven
times is reported beside it as a reference, not as the bar.

**Why.** Hourly demand has a daily shape and a weekly shape, and the same-hour-last-week
value carries both for free. It is the most a forecaster gets without a model, it is what an
honest skill score is measured against, and a model that cannot clear it at a given lead
has nothing to say at that lead. The last-day baseline is there because it is what people
reach for first and because at leads 1 to 24 it is actually the stronger of the two.

**What it costs.** The seasonal naive carries a holiday from the week before into a normal
week and a normal week into a holiday, so it is worst on exactly the days a calendar helps
with. That is a property of the baseline, not a flaw in the comparison, and the day-type
table in the findings reads the model's gain on those days separately.

**What would reverse it.** Nothing. A baseline is a fixed point.

## D-05 One linear model per lead, with no weather in it

Date: 2026-09-05

**Decision.** For each of the 168 leads, an ordinary least squares regression of the target
hour's demand on sixteen things known at the origin: a constant; the same hour one and two
weeks before the target; the same hour on the origin day; the mean of the origin day; the
mean of the origin week; the last hour before the origin; whether the target day is a
Saturday, a Sunday or a holiday; and three pairs of annual sine and cosine terms on the
target day's day of year.

**Why this and not something bigger.** The brief was a forecast whose every step can be
defended line by line, against an honest baseline, with calibrated intervals. Sixteen
coefficients per lead can be printed and read. The features are the ones a forecaster would
name unprompted: last week, yesterday, the current level, the calendar, the season. Fitting
one regression per lead is the direct strategy for multi-step forecasting; it avoids
feeding a forecast back in as an input, so an error at lead 1 does not compound into lead
168.

**Why no weather.** Temperature drives Ontario demand more than anything else, and the data
here has none. Using the temperature that actually occurred on the target day would be
using the future, and a forecast scored that way would look far better than any forecast
that could have been issued. Using archived weather forecasts would be the right design,
and no free archive of Ontario weather forecasts was in scope for this build. So this is a
calendar-and-history forecast, and it is stated as the floor a weather-fed forecast has to
beat rather than as a competitor to one.

**Alternatives considered.** A seasonal ARIMA with a 168-hour season on twenty years of
hourly data does not fit in reasonable time. Exponential smoothing in the library available
handles one seasonal period, and this series has two. A gradient-boosted model would
probably score better and cannot be read coefficient by coefficient; it is the natural next
step, not the first one.

**What it costs.** Two features coincide at any lead that lands on hour 24, because the same
hour on the origin day is then the last hour before the origin. Least squares splits one
coefficient between them, which is harmless for the forecast and misleading in a table, so
the coefficient table is printed for noon and evening leads.

**Measured.** Day ahead, MAE 523 MW (3.0% of demand) against 1,221 for the seasonal naive
and 792 for the last-day naive, skill 57.2%; week ahead 1,029 against 1,214, skill 15.2%;
all leads 878 against 1,219, skill 28.0%. The coefficients say what the skill curve says: at
lead 12 the last hour before the origin carries 1.129 and the same hour last week minus
0.047, so a day ahead the model is the current level with a calendar; at lead 162 no lag
carries more than 0.36 and the intercept and annual terms take over.

**What would reverse it.** An archive of weather forecasts. Then temperature enters as a
feature and the comparison is against this model, not against the naive.

## D-06 Refit every four weeks on a trailing five-year window

Date: 2026-09-05

**Decision.** The model is refit every 28 origins on the five years of origins whose seven
target days were all observed before the refit block starts. It then forecasts the next 28
origins. No fit ever sees an outcome from its own forecast window.

**Why.** The province being forecast is not the province of 2005. Annual mean demand fell
for most of a decade and has been rising since 2021, so a model fit on all of history
learns a level that is wrong for today. Five years is long enough to hold sixteen
coefficients per lead steady and short enough to track the level. Refitting every four
weeks is cheap and mirrors how a forecast is actually run.

**What it costs.** The earliest refits in the calibration year train on a window that
includes 2020, when demand dropped for reasons no calendar term explains. That is what the
calibration year is for; none of its scores are reported.

**What would reverse it.** A refit-interval or window-length sensitivity that moved the
day-ahead error materially. Neither has been run; both are cheap and are listed as next
steps.

## D-07 Intervals come from the distribution of past errors, not a formula

Date: 2026-09-05

**Decision.** For each origin and each lead, the interval around the point forecast is the
forecast plus the quantiles of that lead's out-of-sample errors over the 365 origins ending
seven days before the origin. Eighty percent uses the 10th and 90th percentiles, ninety-five
the 2.5th and 97.5th. The seasonal naive gets intervals built the same way, so its
calibration can be judged beside the model's.

**Why.** A regression's textbook prediction interval assumes errors that are normal and the
same size all year, and hourly demand errors are neither. Empirical quantiles make no such
claim, they are the same construction for both forecasts, and they are judged by one thing
only: does an 80% band contain the outcome 80% of the time. The window ends seven days
before the origin so that every error in it is fully observed at the origin, which is the
condition that makes the coverage figure honest.

**What it costs.** A trailing year carries last winter's calm into this summer's volatility,
and the month-by-month coverage table shows the bands narrowest where the errors are
widest. A trailing eight-week window was run as a sensitivity to see whether a shorter
memory fixes that; the result is in the findings, and it is not a clean fix.

**Measured.** The model's 80% day-ahead band is 1,563 MW wide and covers 77.5% of hours; at
95% it is 2,573 MW wide and covers 93.8%. The baseline's cover 79.0% and 94.7% at 3,824 and
7,257 MW. In June to August the model's 80% band covers 70.3% against 80.5% in the other
months, and 58.6% in July 2025. The 56-day window covers 73.5% in summer and 76.1% elsewhere
with a summer band 200 MW wider, so the trailing year stays as the reported construction.

**What would reverse it.** A model of the error's size by season and hour, which would let
the bands widen in summer without widening all year. That is the next step on intervals.

## D-08 A missing hour is filled from its neighbours and flagged

Date: 2026-09-05

**Decision.** The hourly fact table is built on a generated spine of every hour between the
first and last published hour. Where the source has no row, the value is the rounded mean
of the hour before and the hour after, and a `filled` flag is set on the row.

**Why.** Every forecast in this notebook is a lookup of earlier rows. A hole in the series
becomes a hole in the same-hour-last-week feature exactly one week later, for one lead of
one origin, and a null there would drop a whole day of forecasts. One interpolated hour is
a far smaller distortion than a missing day of scores. The flag travels into the export so
a dashboard can exclude the hour.

**What it costs.** The filled hour is a guess. It is counted in the assertion table, and the
count is expected to equal the number of spine gaps, so a fill that happens for any other
reason would show.

**Measured.** One gap in 213,456 hours: 2025-05-01 hour 1, filled at 13,074 MW between
neighbours of 13,795 and 12,352. B5 and B10 both read 1.

**What would reverse it.** More than a handful of missing hours. Then the fill is no longer
a footnote and the notebook should stop rather than interpolate.

## D-09 The 2003 blackout stays in the data

Date: 2026-09-05

**Decision.** The check that looks for hours below half of the same hour a week earlier is
kept as a recorded note, not a filter. The hours it finds are real and remain in the fact
table.

**Why.** The check was written to catch data errors, and what it caught was the afternoon of
14 August 2003, when the province lost most of its load in a single hour and took a day to
recover. An outlier that is an event is not an error, and a series that had it removed
would be a series that never happened. It sits outside every training window used here, so
it touches no forecast.

**What would reverse it.** A training window that reached back to 2003. Then the question is
whether to exclude those days from the fit, and the answer would probably be yes.

## D-10 The holiday calendar is computed by rule and committed as a crosswalk

Date: 2026-09-05

**Decision.** Ontario's holidays are generated from their rules for every year in the data
and written to `crosswalks/ontario_holidays.csv`. On later runs the committed file is read
first and only new rows are added, so a hand correction survives a rerun. A holiday that
falls on a weekend is observed on the next free weekday. The Civic Holiday is included and
flagged as not statutory.

**Why.** The demand file does not know what day it is. A statutory holiday on a Tuesday
looks like a Sunday to the grid, and the seasonal naive, which copies the week before, gets
those days badly wrong. Computing the calendar rather than typing it means every year is
covered the same way; committing it means a reader can check it. The Civic Holiday is in
because most of the province takes it and the load shows it, whether or not the statute
does.

**What it costs.** Observance rules for weekend holidays are a judgement, and some employers
observe a different day. The `actual_date` column is kept so the alternative is one edit
away. Bridge days and the week between Christmas and New Year are not treated specially.

**What would reverse it.** A measured error on the days around holidays that a
day-after-holiday flag would fix. The day-type error table is where that would show.

## D-11 Zonal demand is dashboard context, not a model input

Date: 2026-09-05

**Decision.** Load the zonal report, check it against the provincial total, and keep the
hourly zonal fact from January 2024 for the dashboard and its security role. Do not
forecast zones.

**Why.** The brief is a provincial forecast. The zones give the dashboard a map and give
the row-level-security role something realistic to filter, which is the reason they are
loaded at all. Forecasting ten zones would be ten more of the same design and would not
change the finding.

**What the load found.** The difference column is written with a quoted thousands separator
when it reaches four digits, which a sniffed CSV dialect splits into two fields and fails
the load on one row. The quote character is set explicitly and the separator is stripped
before the cast. The ten zones do not sum to the published zone total on a large share of
rows, almost entirely by a megawatt or two of rounding; the notebook prints the largest gap
and the count above 5 MW so the reader can see it is rounding.

**Measured.** 129 of 204,695 rows carry the separator, all in the difference column. The
zones miss the total on 72,152 rows, 4 of them by more than 5 MW, the largest by 531 MW on
2012-05-06; the published difference misses on 29,814 rows by at most 75 MW; 35 hours on two days
in 2016 have every zone at zero. Toronto is 35.7% of 2025 zonal demand, Southwest 19.3%,
West 11.3%, Bruce 0.7%.

**What would reverse it.** A user whose decision is regional.

## D-12 The cost of error is stated in days, not dollars

Date: 2026-09-05

**Decision.** The decision framed for the forecast is a large consumer's choice to curtail
tomorrow because it might be one of the five highest-demand hours of the base period, which
is what sets that consumer's share of the global adjustment charge under Ontario's
industrial conservation programme. The forecast's usefulness for that decision is measured
as the gap between the fifth and sixth highest daily peaks of each base period, compared
with the day-ahead error at the peak, and as the number of days that fall within that
error of the fifth peak. No dollar figure is quoted.

**Why.** The dollar cost of a wrong curtailment call depends on the consumer's own load,
its tariff class and its cost of interrupting production, none of which is in this data. A
number in days a consumer would have had to curtail to be sure of catching the five is
measurable from the demand series alone and is the quantity the decision actually turns on.

**What it costs.** The framing is one user's decision. An operator's cost of error runs
through reserve and balancing, and pricing that needs a price series this project does not
load.

**Measured.** The model's day-ahead peak error is 646 MW with a bias of minus 144. The
fifth-to-sixth margin has a median of 128 MW over the 24 complete base periods and is
smaller than the error in 23 of them; in 2025-26 it was 148 MW and 10 days sat within one
peak error of the fifth. In every base period since 2019-20 except 2023-24, all five top
days fell in June to August.

**What would reverse it.** A price series and a stated position. Then the error can be
priced, and the honest way to do it is as a range over positions rather than one figure.

## D-13 Significance by Diebold-Mariano with an overlap correction

Date: 2026-09-05

**Decision.** The gap between the model's and the baseline's absolute errors is tested with
a Diebold-Mariano statistic on the daily series of losses, once per lead bucket on each
day's mean absolute error over the bucket's leads, and once for two single leads. The
variance is corrected with a Bartlett kernel whose lag is the number of days two forecasts
in the bucket can overlap, plus one.

**Why.** Forecasts issued on consecutive days for the same target hours share information,
so their loss differences are autocorrelated and a plain t-test would overstate the
evidence. The bucket version answers the question the score table asks; the single-lead
version shows how much thinner the evidence gets at one hour of one day a week out.

**What would reverse it.** Nothing about the method. The lag choice is a convention, and a
longer one would only make the statistics smaller.

**Measured.** Day ahead 12.8, the 11:00-issue bucket 10.1, two days ahead 9.0, days 3 to 6
5.3, week ahead 3.1 (p = 0.0017), all leads 6.7; single lead 24 10.3; single lead 168 1.4
(p = 0.17). The week-ahead skill is real as a bucket and not at its last hour.

## D-14 The plain yearly file is the one loaded

Date: 2026-09-05

**Decision.** Each year exists on the server as a plain file and as one or more versioned
copies. The notebook loads the plain file and hashes the highest-numbered versioned copy
against it, recording how many years differ.

**Why.** Nothing on the report page says which is canonical. Hashing settles whether the
question matters; where the copies are identical it does not, and the data contract says
so with the count.

**What would reverse it.** A year whose versioned copy differs from the plain file. Then the
data contract has to say which was loaded and why, and the assertion that counts the
difference is what would raise it.

**Measured.** 25 years with a versioned copy, 25 identical to the plain file.
