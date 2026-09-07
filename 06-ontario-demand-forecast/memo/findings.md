# Findings: how far a calendar-and-history forecast gets, and what its intervals are worth

Measured on the 2026-09-06 pull of the IESO hourly demand reports, 25 yearly files from 2002
to 2026 and 213,456 hours, scored on every day from 2025-01-01 to 2026-08-31. Every number
below has a row in `mart_score`, `mart_coverage`, `mart_daily_peak`, `mart_ici_margin` or one
of the other mart tables behind it, and the notebook produces all of them top to bottom.

## The one-paragraph version

Issued at midnight for the next 24 hours, a linear model with sixteen inputs per lead and no
weather in it misses Ontario's hourly demand by 523 MW on average, which is 3.0% of demand.
The same-hour-last-week forecast misses by 1,221 MW, so the model removes 57% of the
baseline's error a day ahead. A week ahead it removes 15%, 1,029 MW against 1,214, and at
the single lead of midnight on the seventh day the two forecasts cannot be told apart. Its
80% interval is 1,563 MW wide at a day ahead and contains the outcome 77.5% of the time; the
baseline's 80% interval covers 79.0% of hours but is 3,824 MW wide to do it. Both fail in the
same place: in June, July and August the model's 80% band covers 70% of hours, and a band
with an eight-week memory instead of a year covers 73.5% while widening by 200 MW. On the
hottest day of the window the model under-called the afternoon by about 2,000 MW, because
nothing in its inputs knew a heat wave was coming. For a large consumer deciding whether to
curtail tomorrow, the day-ahead error at the peak, 646 MW, is five times the 128 MW median gap
between the fifth and sixth highest daily peaks of a base period; in 23 of 24 base periods the
gap is smaller than the error, so this forecast cannot pick the five days that set the charge,
and in 2025-26 a consumer relying on it would have had to treat 10 days as candidates.

## First, what the source did

Three things in the files would have gone wrong quietly if the checks had not been written
before the model was.

**An hour is missing from a closed year.** The 2025 file carries 8,759 rows where a year has
8,760 hours, and the day with 23 rows is 2025-05-01, whose first hour is simply absent: hour
24 of April 30 reads 13,795 MW, hour 2 of May 1 reads 12,352, and there is no hour 1 between
them. Nothing in the file marks it. A weekly lag that landed on that hole would have dropped
one lead of one origin exactly a week later, so the hour is filled with the mean of its
neighbours, 13,074 MW, and flagged. It is the only gap in 213,456 hours.

**The zonal report writes one column with a quoted thousands separator.** When the
difference between the zone total and Ontario demand reaches four digits it is written as
`"-1,054"`. A CSV reader that guesses the dialect sees no quoting elsewhere in the file,
splits that value on its comma, and fails the load on a row with sixteen fields. It happens
on 129 of 204,695 rows, all in that one column, which is few enough to be missed in any sample
a sniffer takes. The quote character is set explicitly and the separator stripped before the
cast. The same report has three hours on 2016-05-29 where every zone reads zero and the
published difference is minus the whole province, and 72,152 rows where the ten zones do not
sum to the published total, all but four of them by 5 MW or less, which is rounding.

**An outlier check finds an event.** Hours below half of the same hour one week earlier
should be data errors. There are 12 of them, from 15:00 on 14 August 2003 to 02:00 the next
morning, the afternoon Ontario lost most of its load in the Northeast blackout: 2,270 MW at
hour 17 against 21,894 a week before. They are real and they stay. They also sit fifteen years
before the earliest training window, so they touch no forecast.

Two smaller facts about the clock and the copies. Every date in 24 years carries exactly 24
rows, including the March and November clock-change days, so the series runs on a fixed
standard-time clock and a 168-hour lag always lands on the same wall-clock hour. And each
year exists on the server twice, as a plain file and a versioned copy; the two hash identical
for all 25 years, so which one is loaded does not matter.

## How the backtest is set up

The series runs from 2002-05-01, the day Ontario's wholesale market opened, and the analysis
matrix holds 8,889 days to 2026-08-31, one row per day and one column per hour. An origin is
the end of a day; its targets are the 168 hours of the seven days after it. Every day from
2024-12-31 to 2026-08-24 is a test origin, 602 of them, chosen so that all seven target days
of every origin fall inside the window and every lead is scored the same number of times.

Three forecasts per origin:

- **Seasonal naive.** The demand at the same hour of the same weekday one week before the
  target. It is the baseline: the most a forecaster gets for free, and it knows nothing about
  holidays, weather or trend.
- **Last-day naive.** The origin day's 24 hours repeated seven times. A second reference, and
  at leads 1 to 24 the stronger of the two baselines.
- **The model.** For each of the 168 leads, ordinary least squares on sixteen things known
  at the origin: a constant, the same hour one and two weeks before the target, the same hour
  on the origin day, the mean of the origin day, the mean of the origin week, the last hour
  before the origin, whether the target day is a Saturday, a Sunday or a holiday, and three
  pairs of annual sine and cosine terms on the target day's day of year. Refit every 28
  origins on the five years of origins whose targets were all observed before the block:
  1,825 origins per fit, 35 refits, 5,880 fits in all. No fit sees an outcome from its own
  forecast window.

The year before the test window, 372 origins, is scored and never reported. Its errors are
what the prediction intervals are built from, so an interval is never judged by an error it
has already seen.

Two things about the province being forecast, from the yearly table. Mean demand fell from
17,919 MW in 2005 to 15,053 MW in 2020 and has risen every year since, to 16,621 MW in 2025
and 17,086 MW over the first eight months of 2026, which is why the model trains on a trailing
five years rather than on everything. And the day type matters more than a model with no
calendar would guess: in 2025 the average weekday ran 16,903 MW against 16,006 on a Sunday and
15,703 on a holiday, and at hour 8 the gap between a weekday and a Sunday is 2,144 MW.

## The score

Mean absolute error in megawatts over the 602 test origins, by lead bucket. Skill is the
share of the seasonal naive's error the model removes.

| Leads | Seasonal naive | Last-day naive | Model | Model RMSE | Model MAPE | Skill |
|---|---|---|---|---|---|---|
| **Day ahead, 1 to 24** | 1,221 | 792 | **523** | 737 | 3.0% | **57.2%** |
| Day ahead as issued at 11:00, 13 to 36 | 1,221 | 958 | 669 | 895 | 3.9% | 45.2% |
| Two days ahead, 25 to 48 | 1,221 | 1,128 | 780 | 1,055 | 4.5% | 36.1% |
| Days 3 to 6, 49 to 144 | 1,219 | 1,266 | 954 | 1,266 | 5.5% | 21.8% |
| **Week ahead, 145 to 168** | 1,214 | 1,214 | **1,029** | 1,350 | 5.9% | **15.2%** |
| All leads, 1 to 168 | 1,219 | 1,171 | 878 | 1,189 | 5.0% | 28.0% |

Mean demand over the window is 16,800 MW and the mean absolute change from one hour to the
next is 444 MW, so the day-ahead error is about an hour and a quarter of ordinary movement.
The seasonal naive's error is flat across the week by construction, since it looks up the
same distance back for every lead. The model's error climbs through the week and its daily
rhythm is visible in the first chart: within each day the error peaks in the afternoon and
bottoms at night, and by day seven the afternoon peak of the model's error sits only a couple
of hundred megawatts under the baseline's.

The first day is where the model earns its keep, and most of that is the first twelve hours.
At lead 1 the error is 130 MW; by lead 12 it is 700; by lead 24 it is 550 again because
midnight is quiet. The last-day naive, which nobody would defend as a forecast, beats the
seasonal naive over the first day (792 against 1,221) because yesterday's level is closer
than last week's, and the model's largest coefficients say the same thing.

## Is the gap real

A Diebold-Mariano test on the daily series of absolute errors, corrected for the overlap
between consecutive forecasts. Positive gain means the model loses less.

| Leads | Naive MAE | Model MAE | Mean gain, MW | DM statistic | p-value |
|---|---|---|---|---|---|
| Day ahead, 1 to 24 | 1,221 | 523 | 698 | 12.8 | less than 0.0001 |
| Day ahead as issued at 11:00, 13 to 36 | 1,221 | 669 | 552 | 10.1 | less than 0.0001 |
| Two days ahead, 25 to 48 | 1,221 | 780 | 441 | 9.0 | less than 0.0001 |
| Days 3 to 6, 49 to 144 | 1,219 | 954 | 265 | 5.3 | less than 0.0001 |
| Week ahead, 145 to 168 | 1,214 | 1,029 | 185 | 3.1 | 0.0017 |
| Single lead 24 | 1,080 | 552 | 528 | 10.3 | less than 0.0001 |
| Single lead 168 | 1,068 | 978 | 90 | 1.4 | 0.17 |

The improvement is not a run of luck at any bucket, including the week-ahead one. It is
thin at the far end, though: at the single lead of midnight on day seven the model's 90 MW
gain over the baseline has a p-value of 0.17, which is to say that after a week the model is
back to being a slightly better seasonal naive with a calendar attached. Anyone quoting the
week-ahead skill should quote it with that.

## Where the model is weak

**By the type of day forecast, day ahead.** The seasonal naive copies last week, so a
holiday that falls on a weekday is its worst case by construction, and it is also where the
model's calendar term does the most.

| Target day type | Days | Naive MAE | Model MAE | Skill |
|---|---|---|---|---|
| Holiday | 16 | 2,251 | 561 | 75.1% |
| Saturday | 86 | 1,052 | 500 | 52.4% |
| Sunday | 86 | 1,192 | 549 | 53.9% |
| Weekday | 414 | 1,223 | 521 | 57.4% |

The model's error is nearly the same on every kind of day, which is what a calendar term
should achieve. The baseline's error on a holiday is nearly double its error on a weekday.

**By month, day ahead.** The model's error runs from 331 MW in May 2025 and 357 MW in
January 2026 to 722 MW in June 2025 and 771 MW in July 2025, with July 2026 at 692. As a
share of demand that is 1.9% in January 2026 against 4.4% in June 2025. The baseline's worst
months are the same ones and far worse: 2,383 MW in July 2025 and 2,494 MW in August 2025.
Summer is where demand moves with the weather from one day to the next, and a forecast with
no weather in it has nothing to move with.

## Are the intervals calibrated

An 80% interval should contain the outcome 80% of the time. Each interval here is the point
forecast plus the 10th and 90th (or 2.5th and 97.5th) percentiles of that lead's own errors
over the 365 origins ending seven days before the origin, built the same way for the model
and for the baseline.

| Forecast and leads | 80% coverage | 80% width, MW | 95% coverage | 95% width, MW |
|---|---|---|---|---|
| Model, day ahead | 77.5% | 1,563 | 93.8% | 2,573 |
| Model, week ahead | 78.5% | 2,749 | 93.8% | 4,688 |
| Model, all leads | 78.3% | 2,446 | 94.0% | 4,218 |
| Seasonal naive, day ahead | 79.0% | 3,824 | 94.7% | 7,257 |
| Seasonal naive, week ahead | 79.3% | 3,820 | 94.7% | 7,246 |

Across five nominal levels the model's day-ahead intervals cover 48.5%, 77.5%, 88.4%, 93.8%
and 97.3% against 50, 80, 90, 95 and 98 nominal, so they run one to three points under what
they promise at every level, and the baseline's run within about a point. That is the
second chart. The reason the baseline looks better calibrated is that its errors are large
and steady, so a year of them describes next week well; the model's errors are small and
change with the season, so a year of them describes next week less well. Calibration is
bought with width, and the model's 80% band is 41% of the baseline's.

**By month.** Coverage of the model's 80% day-ahead band ranges from 90.9% in May 2025 and
90.2% in January 2026 to 58.6% in July 2025, 63.0% in March 2025, 67.6% in June 2025 and 68.7%
in July 2026. The baseline's band does the same in the summer, 34.8% in July 2025 and 41.1% in
August 2025, while covering over 95% in the calm months. Both bands are built from a trailing
year of errors, so they carry last winter's calm into this summer's volatility.

**A shorter memory does not fix it.** Rebuilding the model's day-ahead bands from the
trailing 56 origins instead of 365:

| Residual window | Nominal | Coverage, all months | Coverage, June to August | Coverage, other months | Width, MW | Width in summer, MW |
|---|---|---|---|---|---|---|
| 365 days | 80% | 77.5% | 70.3% | 80.5% | 1,563 | 1,572 |
| 56 days | 80% | 75.4% | 73.5% | 76.1% | 1,545 | 1,771 |
| 365 days | 95% | 93.8% | 90.4% | 95.3% | 2,573 | 2,582 |
| 56 days | 95% | 90.4% | 89.9% | 90.6% | 2,370 | 2,853 |

The short window buys three points of summer coverage with a band 200 MW wider in summer,
and pays for it with four points of coverage lost in the rest of the year, because a quantile
taken from 56 numbers is noisy. The trailing-year band is the one reported. What would fix
summer is a band that widens with the season by design rather than by memory, and that is the
next step on intervals, not a tuning of this one.

## The daily peak

Most users of a demand forecast care about one number a day. From the forecast issued at the
midnight before, over 602 days:

| Forecast | Peak MW error, MAE | Peak MW bias | Error at the actual peak hour, MAE | Peak hour exact | Peak hour within an hour |
|---|---|---|---|---|---|
| Seasonal naive | 1,293 | minus 19 | 1,329 | 46.0% | 70.8% |
| Model | 646 | minus 144 | 701 | 54.3% | 80.2% |

The mean daily peak over the window is 19,046 MW, so the model's peak error is 3.4% of it. The
bias is the number to notice: the model under-calls the peak by 144 MW on average, where the
baseline is unbiased, because a regression toward a five-year mean pulls the extremes in. A
user who acts on peaks would add that back.

**The hottest day of the window, read row by row.** Tuesday 2026-07-14, from the origin of
the night before. The actual peak was 25,646 MW at hour 17. The model called 24,035 MW for that
hour, 1,611 MW short; its worst hours were 13 and 22, at 2,368 and 2,389 MW short. It had the
first six hours of the day within 300 MW, and then the day pulled away from it. Its error over
the day was 1,299 MW against the baseline's 2,625, and 7 of 24 hours fell inside its 80%
band. That is what a forecast with no weather does on the one day everyone remembers: it
knows the shape and not the level.

## Who acts on this, and what the error costs

Ontario's largest consumers pay their share of the global adjustment charge according to
their own draw during the five highest-demand hours of the May-to-April base period, each on a
different day. The decision a day-ahead forecast informs is whether to curtail tomorrow
because it might be one of those five days. What that takes is resolving the gap between the
fifth-highest daily peak of the period and the sixth.

Measured on every base period on record:

- The median gap between the fifth and sixth highest daily peaks over the 24 complete base
  periods, 2002-03 to 2025-26, is 128 MW. In 2005-06 it was 8 MW and in 2015-16 it was 3 MW.
  The widest was 724 MW, in 2013-14.
- The model's day-ahead peak error is 646 MW. It is larger than the gap in 23 of the 24
  periods.
- In 2025-26 the top five peaks ran from 24,862 MW down to 24,211, the sixth was 24,063, the
  gap was 148 MW, and 10 days had a peak within 646 MW of the fifth. A consumer relying on this
  forecast to catch the five would have curtailed on all 10. In 2014-15 the same rule would
  have meant 32 days.
- All five top days fell in June, July or August in every base period since 2019-20 except
  2023-24, when two did. The first 129 days of 2026-27 already show a gap of 307 MW and 8
  candidate days.

So the honest statement is that this forecast cannot pick the five days, and neither could
any forecast with an error near 646 MW at the peak, because the days that set the charge are
separated by tens of megawatts. What a forecast at this accuracy does is shrink the set of
days worth watching from a summer to about ten, and the cost of relying on it is curtailing on
twice as many days as strictly needed. A dollar figure would need the consumer's own load and
tariff, which this data does not hold, so the cost is stated in days.

## What the model learned

Coefficients from the final refit, on the raw megawatt scale, so a coefficient of 1 on a lag
means one megawatt of that lag becomes one megawatt of forecast.

| Input | Lead 12, noon on day 1 | Lead 18, evening on day 1 | Lead 162, evening on day 7 |
|---|---|---|---|
| Last hour before the origin | 1.129 | 0.763 | 0.361 |
| Same hour on the origin day | 0.341 | 0.789 | 0.016 |
| Mean of the origin day | minus 0.535 | minus 0.867 | minus 0.289 |
| Mean of the origin week | 0.007 | 0.132 | 0.088 |
| Same hour one week before the target | minus 0.047 | minus 0.034 | 0.016 |
| Same hour two weeks before the target | minus 0.026 | 0.029 | 0.072 |
| Target is a Saturday, MW | minus 907 | minus 725 | minus 998 |
| Target is a Sunday, MW | minus 1,071 | minus 387 | minus 910 |
| Target is a holiday, MW | minus 944 | minus 476 | minus 1,323 |
| Intercept, MW | 4,432 | 4,668 | 14,477 |

Three things it says. A day ahead, the forecast is almost entirely the current level: the last
hour before midnight and yesterday's same hour carry it, and the same-hour-last-week input,
which is the whole of the seasonal naive, gets a coefficient near zero once yesterday is in the
room. A week ahead, none of the lags carry much, the intercept and the annual terms take over,
and the model is a seasonal average with a calendar, which is why its skill at day seven is
15% and not 57%. And the calendar terms are large at every lead: a Sunday is worth about a
thousand megawatts less than a weekday at noon, and a holiday about the same, which is the
error the seasonal naive makes every time a holiday falls on a weekday.

## Reading the numbers

The honest sentence is: with the calendar and the last two weeks of history and nothing
else, hourly Ontario demand can be forecast a day ahead to about 3% and a week ahead to about
6%, which is 57% and 15% better than copying last week, with intervals that are a few points
overconfident and badly overconfident in summer. Every one of those gaps is a weather gap, and
the model is the floor a weather-fed forecast has to beat, not a competitor to one.

## What this cannot tell you

- **What a weather-fed forecast would do.** No temperature, no weather forecast archive, no
  humidity. The summer errors and the summer under-coverage are what that absence looks like.
- **What the operator's own forecast did over the same hours.** The report carries actuals
  only, so the comparison is with a baseline, not with the IESO.
- **Anything at intraday origins.** One origin per day at midnight. A dispatcher updating at
  11:00 has twelve more hours of information than this model, and the 13 to 36 bucket is the
  nearest this design gets to that.
- **The dollar cost of an error.** No price series, no tariff, no consumer's load. Days
  curtailed is the unit this data supports.
- **The five days themselves.** The fifth-to-sixth gap is tens of megawatts in most base
  periods, and the forecast's error at the peak is hundreds. That is a statement about the
  problem, not about this model.
- **Zonal demand.** Loaded, checked and exported for the dashboard; not forecast.
- **Whether a different refit interval or training window would score better.** Neither
  sensitivity was run. Both are cheap and are the first things to try.

## Definitions

- **Origin.** The end of hour 24 of a day. Forecasts are issued there for leads 1 to 168, the
  hours of the next seven days.
- **Lead.** Hours after the origin. Lead 1 is the hour starting at midnight; lead 24 is the
  hour starting at 23:00 on day one; lead 168 is the last hour of day seven.
- **Test window.** Origins from 2024-12-31 to 2026-08-24, 602 of them, whose target days all
  fall between 2025-01-01 and 2026-08-31.
- **Seasonal naive.** For a target hour, the demand 168 hours earlier.
- **Last-day naive.** For a target hour, the demand at the same hour of the origin day.
- **Model.** One ordinary least squares regression per lead on the sixteen inputs listed
  above, refit every 28 origins on the previous 1,825 origins with fully observed targets.
- **MAE, RMSE, MAPE.** Mean absolute error in MW; root mean squared error in MW; mean of
  absolute error divided by actual demand.
- **Skill.** One minus the model's MAE divided by the seasonal naive's MAE, over the same
  leads and origins.
- **Diebold-Mariano statistic.** The mean of the daily loss differential (baseline absolute
  error minus model absolute error) divided by its standard error, the variance estimated with
  a Bartlett kernel whose lag is the number of days two forecasts in the bucket can overlap,
  plus one. The p-value is two-sided from the normal.
- **Interval at level p.** The point forecast plus the (1 minus p)/2 and 1 minus (1 minus p)/2
  quantiles of the lead's residuals (actual minus forecast) over the 365 origins ending seven
  days before the origin.
- **Coverage.** The share of test hours whose actual demand fell inside the interval.
- **Peak MW error.** The forecast's maximum over leads 1 to 24 minus the actual maximum.
  **Error at the actual peak hour** is the forecast at the hour the actual peak occurred,
  minus that peak.
- **Base period.** May 1 to April 30, labelled by its starting year. **Fifth-to-sixth gap** is
  the fifth-highest daily peak of the period minus the sixth, each on a distinct day.
  **Candidate days** are days whose peak is within the model's day-ahead peak MAE of the fifth.

## Data quality checks

The table the notebook renders as `dq_assertions`, with the count measured on this pull.
BLOCK stops the build until a decision is written; WARN is flagged and carried; NOTE is
recorded.

| id | Severity | Rule | Expected | Found | Decision |
|---|---|---|---|---|---|
| B1 | BLOCK | duplicate (date, hour) key in the staged demand table | 0 | 0 | stop if any |
| B2 | BLOCK | pulled file whose header differs from the one read before the pull | 0 | 0 | stop and re-read the header |
| B3 | BLOCK | pulled file whose inside year differs from the year in its name | 0 | 0 | stop and check the listing |
| B4 | WARN | demand value that failed the integer cast | measure | 0 | carried as null, filled on the spine if isolated |
| B5 | WARN | hour missing from the spine between the first and last published hour | measure | 1 | filled with the mean of its neighbours and flagged |
| B6 | WARN | date before the window end with other than 24 rows | measure | 1 | explained by B5; no clock-change days among them |
| B7 | WARN | hour where market demand is below Ontario demand | measure | 43 | recorded; Ontario demand is the target and is not adjusted |
| B8 | NOTE | hour below half of the same hour one week earlier | measure | 12 | a real event, kept; outside every training window |
| B9 | BLOCK | date in the hourly series with no calendar row | 0 | 0 | stop; extend the calendar |
| B10 | NOTE | filled hour in the fact table | 1 | 1 | equals B5 by construction |
| B11 | WARN | zonal row where the zones do not sum to the published zone total | measure | 72,152 | recorded; all but 4 within 5 MW; zonal data is dashboard context only |
| B12 | WARN | zonal row where zone total minus Ontario demand is not the published difference | measure | 29,814 | recorded; largest gap 75 MW |
| B13 | NOTE | year whose versioned copy differs from the plain yearly file | measure | 0 | the plain yearly file is the one loaded |
| B14 | BLOCK | day inside the test window missing from the series | 0 | 0 | stop; the window end must sit inside the published data |
| B15 | BLOCK | export whose written row count differs from its source table | 0 | 0 | stop and re-export |
| B16 | BLOCK | scored origin with no model forecast | 0 | 0 | stop; the refit loop left a gap |
| B17 | WARN | zonal row with a number written with a thousands separator | measure | 129 | quote character set, separator stripped before the cast |
| B18 | BLOCK | zonal value that failed the integer cast after the separator was stripped | 0 | 0 | stop; a value did not cast |

Eight blocking rules passed, seven warnings carried, three notes recorded. The seven tables
exported for the dashboard reconciled row for row: 213,336 hours, 303,408 forecast rows,
233,750 zonal rows, 9,009 dates, and the three small dimensions.
