# Findings: what the import data can and cannot say about additive manufacturing

Measured on the Canadian International Merchandise Trade import files pulled 2026-09-05 and
2026-09-06, thirty-nine yearly zips from 1988 to July 2026, and the code dictionary shipped
inside the 2026 zip, cut for July 2026. Every number below has a table in the dbt project or a
cell in the notebook behind it, and the notebook produces all of them top to bottom, which it
did on 2026-09-09.

## The one-paragraph version

Canada's import statistics classify goods by a ten-digit code whose meaning changes. Code
8485100000 meant ships' propellers from 1988 to 2006 and has meant metal 3D printers since
January 2022, and it is one of 5,962 codes with more than one meaning in the dictionary. A join
on the code alone attaches today's meaning to every year: across 1988 to 2026 it would
misdescribe 8.49 percent of import value and lose another 35.24 percent under codes that no
longer exist, 43.73 percent of 15,970 billion nominal dollars, and in 1988 it would get 89.13
percent of the year wrong. Joined on the code and the month against the dictionary's own
validity ranges, every one of 186,229,882 rows lands on exactly one meaning. On that footing the
additive manufacturing series reads as follows. Imports under the nine 3D-printing codes were
49.5 million dollars in 2022 and 116.1 million in 2025, a rise of 134.8 percent that a reader of
the published series cannot compare with anything earlier, because before 2022 the goods were
inside seventeen machinery codes that the publisher's own concordance names. Those seventeen
codes are fifty times larger than the printers and their basket shows no measurable fall in
2022; the one donor that does fall, the plastics machinery code, gave up about a quarter of its
level, which bridges the plastics printers back to a 2021 level of 26.0 million dollars against
62.7 million in 2025, a rise of 141.7 percent with a bootstrap interval from 36.2 to 1,463.0
percent. Carbon fibre cannot be read as a series at all: it has five stretches under four
regime labels between 1988 and 2026, and no code carries it cleanly across any boundary.

## First, the trap in the source

The dictionary that ships with every zip is a fixed-width text file, 53,570 lines of exactly 213
characters, Windows-1252, eight fields, with the start and end month of every code's meaning.
Every delimited reader I tried took the first line as a header and misread the rest. Parsed on
measured column positions, it holds 42,771 distinct codes, 8,631 of them with more than one
validity period, 5,962 with more than one distinct English description, and 10,930 with an open
period today, of which 2,288 previously meant something else. No two periods of a code overlap.

The dictionary is a snapshot, not a file. The copy in the zips for 1988 to 2018 was cut in July
2021 and holds 52,022 code-periods; the copy in the 2026 zip holds 53,570. The newest copy
restates 129 periods of the oldest one with a different description, so the notebook parses all
eight distinct snapshots the backfill kept and compares each with the newest before the newest
is used for everything.

The reclassification this project is built around is one date in that dictionary. 852 codes
end in December 2021 and 1,355 begin in January 2022: 424 are the same code carrying on, 332
of them with a new description, 428 were retired and 931 created. Heading 8485 had no live code
at all in December 2021.

## What a join on the code alone does to the numbers

The fact table carries, for every row, whether a join on the code alone would have attached the
same description the temporal join did, a different one, or none at all because the code has no
current period. By year:

| Year | Value, billion CAD | Misdescribed | Orphaned | Wrong under the naive join | Codes misdescribed |
|---|---|---|---|---|---|
| 1988 | 131.3 | 11.11% | 78.02% | 89.13% | 1,019 |
| 1997 | 272.9 | 8.30% | 73.92% | 82.23% | 991 |
| 2006 | 397.0 | 11.77% | 62.71% | 74.48% | 656 |
| 2011 | 446.7 | 11.55% | 52.61% | 64.16% | 689 |
| 2016 | 533.3 | 13.54% | 29.80% | 43.34% | 706 |
| 2021 | 616.6 | 9.87% | 8.65% | 18.52% | 333 |
| 2022 | 744.4 | 0.12% | 0.64% | 0.75% | 19 |
| 2025 | 788.9 | 0.00% | 0.02% | 0.02% | 1 |
| 2026, seven months | 488.2 | 0.00% | 0.00% | 0.00% | 0 |

The steps at 2007, 2012, 2017 and 2022 are the revisions of the Harmonized System. Across all
thirty-nine years, 1,356 billion dollars would be misdescribed and 5,628 billion orphaned, 8.49
and 35.24 percent of 15,970 billion. The 2026 row is zero by construction: that year's zip
shipped the dictionary in use. No import row carries a code missing from the dictionary, so
the fourth bucket is empty.

## How the series are built

The concordance is the publisher's, not mine. Statistics Canada prepared a ten-digit
statistical concordance for the January 2022 tariff, published by the border agency as two
spreadsheets, 2,052 and 455 pairs, 2,507 distinct. Between them they list every code the
dictionary closes in December 2021 and every code it opens in January 2022, and a dbt test
asserts that on every build. The rule I had planned, pair a retired code with new codes in its
subheading or heading, would have found nothing for heading 8485 and, across the 2,083
published pairs where the code changed, would have missed 876: 598 of the moves cross into
another chapter and 278 more cross headings within the chapter. Every one of the 17 pairs that
feed heading 8485 crosses headings inside chapter 84.

Three baskets, defined in `crosswalks/series_definitions.csv` with the rule and source on
every row:

- **Recipients.** The nine codes the dictionary opened under heading 8485 in January 2022.
  In 2025, plastics printers 8485200000 were 54.0 percent of the basket, parts not elsewhere
  specified 8485909000 31.8 percent, metal printers 8485100000 6.2 percent.
- **Donors.** The seventeen 2021 codes the concordance maps to any of the nine, each over its
  unbroken run of periods through the break. The basket starts in January 2019, the first
  month all seventeen exist, which leaves 36 months before the break and 55 after.
- **Combined.** Both together, the one basket whose goods do not change when the heading
  opens, so its growth is the printers plus everything else the donors carry.

| Basket, million CAD | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 to July |
|---|---|---|---|---|---|---|---|---|
| Recipients | | | | 49.5 | 61.0 | 97.8 | 116.1 | 96.7 |
| Donors | 2,105.0 | 2,053.0 | 2,266.0 | 2,401.0 | 2,590.5 | 2,937.1 | 3,238.8 | 1,975.7 |
| Combined | 2,105.0 | 2,053.0 | 2,266.0 | 2,450.5 | 2,651.5 | 3,034.9 | 3,355.0 | 2,072.4 |

One figure this rules out. The brief this project started from quoted a rise to 564 million
dollars of additive manufacturing imports in 2025. The nine codes sum to 116.1 million in that
year, so whatever that figure counts, it is not the codes the tariff names for the machines
and their parts.

The goods that moved are about two percent of the codes they came from. Five donors fell
from 2021 to 2022, led by the plastics machinery code 8477800000 at 13.7 million down; the two
largest donors, both machines not elsewhere specified under 8479, rose by 59.7 and 54.1
million. That was on the record before any test ran, and it is the expectation the tests are
judged against.

## Where the break shows, and where it does not

Every test runs on log monthly value with a linear trend and eleven month dummies, from
January 2019 to July 2026.

**The Chow test at January 2022**, every coefficient free to change before and after, gives F
of 1.46 on 13 and 65 degrees of freedom for the donor basket, p 0.158, and 1.59 for the
combined basket, p 0.110. Of the sixteen donor codes with a positive value in every month,
two clear 0.05: 8475900000 at p 0.002 and 8477903000 at p 0.004, both with the post-break
level below the pre-break fit.

**The rolling Chow scan**, the same statistic at every month with eighteen months kept on each
side, is a locator and not a test, and no critical value is attached to its maximum. It puts
the donor basket's largest F at January 2025 and the combined basket's in the autumn of 2020,
with January 2022 ranking 26th and 27th of 55 candidate months. For the plastics donor the
largest F is at August 2021, five months before the tariff change, with the level 35.4 percent
lower after it; that is what a code losing its printers over the last months of 2021 looks
like, and it is the only series where the scan lands near the date.

**The interrupted time series**, a level shift and a change of slope from January 2022 with
Newey-West standard errors at four lags, is where the sizes are:

| Series | Level shift | Newey-West p | Slope change per month | p | Moved out of the 2021 value, million CAD |
|---|---|---|---|---|---|
| Donor basket | +1.6% | 0.679 | +0.00476 | 0.001 | none: minus 36.5 |
| Combined basket | +3.1% | 0.425 | +0.00534 | 0.000 | none: minus 71.4 |
| 8477800000, plastics machinery | minus 25.9% | 0.026 | +0.01215 | 0.124 | 26.0 |
| 8477903000, hydraulic assemblies | minus 58.6% | 0.000 | minus 0.00789 | 0.122 | 10.4 |
| 8477909090, other parts | minus 16.3% | 0.000 | +0.00419 | 0.024 | 20.2 |

The donor basket did not fall at the break; it rose, and its slope steepened afterwards. So
did the combined basket, which is the result basket invariance predicts if the goods only
moved within it, and it is also what a machinery import boom from 2022 looks like. The three
donors that did fall are all in the rubber and plastics machinery heading, which is where the
plastics printers, the largest recipient, came from. The recipients themselves, with no
pre-period, trend at 40.6 percent a year from 2022.

## Three growth estimates, 2021 to 2025

| Estimate | What it compares | Result |
|---|---|---|
| Published | the recipient codes, 2021 to 2025 | undefined: there was no 2021 value. Inside the published series, 2022 to 2025 is +134.8% |
| Basket-invariant | the combined basket, 2021 to 2025 | +48.1%, printers and everything else the donors carry |
| Bridged, donor basket | recipients in 2025 against the 2021 level the donor basket's level shift implies | undefined: the shift is positive; 1,266 of 2,000 bootstrap replicates gave no negative shift |
| Bridged, plastics pair | plastics printers in 2025 against the 2021 level the plastics donor's shift implies, 26.0 million | +141.7%, bootstrap interval +36.2% to +1,463.0%, 60 of 2,000 replicates undefined |

The bootstrap redraws the interrupted time series residuals in six-month blocks and refits.
The plastics interval is wide because the shift is estimated from 36 pre-break months of one
code; it does exclude zero, and it sits above the basket-invariant figure, which is what a good
growing faster than the machinery around it would produce. The honest sentence is that the
printers grew somewhere between the basket's 48 percent and the published series' 135
percent, that the one bridge the data can build says about 140 percent for plastics printers,
and that the donor codes as a whole are too large to show the move at all.

## Carbon fibre: five stretches, four labels, no series

| Stretch | Regime | Months | Codes | Value, million CAD | Per month |
|---|---|---|---|---|---|
| 1988-01 to 1997-12 | not separately coded | 120 | none | | |
| 1998-01 to 2001-07 | clean code, 6815101000 as carbon fibres and filaments | 43 | 1 | 34.8 | 0.81 |
| 2001-08 to 2014-09 | the same code commingled with refractory brick | 158 | 1 | 216.2 | 1.37 |
| 2014-10 to 2021-12 | not separately coded | 87 | none | | |
| 2022-01 to 2026-07 | split into 6815110000, 6815120000, 6815130000 | 55 | 3 | 228.4 | 4.15 |

The publisher's concordance confirms the gap: it sends the three 2022 codes back to
6815999000, articles of stone or other mineral substances not elsewhere specified. The epoxide
sheet reinforced with carbon fibres is its own short series, 5.3 million over 1988 to 1997 under
3921909014 and 10.9 million over 1998 to 2011 under 3921909914, then nothing of its own. The
chart shades the stretches and draws no line across an edge, and no growth rate is quoted
across one.

## What this cannot tell you

- **Whether reclassified goods are physically the same products.** The concordance is the
  publisher's inference, published without weights. It says which codes fed the printers, not
  how much of each.
- **What the donor basket lost.** The seventeen donors are fifty times the recipients and rose
  through the break. The basket-level bridge is undefined and is reported as such.
- **Growth before 2019.** The donor basket cannot start earlier without a second concordance
  at the January 2019 break inside heading 8477.
- **Real growth.** Every value is nominal Canadian dollars at customs valuation. Nothing is
  deflated.
- **Domestic production or market size.** Import value measures what Canada buys.
- **Where goods are used.** Province is the province of clearance.
- **Materials.** The nine codes are machines and parts; powders, filaments and resins sit in
  chemical headings and are not separated here.
- **Anything after July 2026**, including the tariffs of September 2026.

## Definitions

- **Validity period.** The publisher's start and end month for one meaning of one code; the
  open sentinel 999912 converts to 9999-12-31 so a BETWEEN works.
- **Temporal join.** Import row to dictionary period on the code and the month within the
  period's range. Every row matched exactly one period.
- **Naive join.** Import row to the code's current period, whatever the month.
- **Misdescribed.** Value whose current description differs from the one valid at the time.
  **Orphaned.** Value under a code with no current period.
- **Recipient, donor, combined.** As above, with membership in the committed CSV.
- **Level shift.** The coefficient on a post-break indicator in log value; as a percentage,
  exp of the coefficient minus one. Applied to a donor's actual 2021 value it is the amount
  that left.
- **Bridged growth.** Recipient value in 2025 over the backcast 2021 level, minus one. Defined
  only when the shift is negative.

## Data quality checks

BLOCK stops the build until a decision is written; WARN is flagged and carried; NOTE is
recorded. Counts as measured on the 2026-09-09 run.

| id | Severity | Rule | Expected | Found | Decision |
|---|---|---|---|---|---|
| C1 | BLOCK | dictionary lines failing the fixed-width pattern | 0 | 0 | fix the pattern, not the data |
| C2 | BLOCK | overlapping validity periods within a code | 0 | 0 | stop if any |
| C3 | NOTE | codes with more than one period | 8,631 | 8,631 | modelled |
| C4 | NOTE | codes with more than one distinct description | 5,924 | 5,962 | the newer snapshot; the flag is meaning_changed |
| C5 | BLOCK | import rows matching zero or more than one period | 0 and 0 | 0 and 0 | dbt singular tests |
| C6 | BLOCK | per-year rows equal the run log, twelve months per completed year | all | all 39 | a failing year is re-run |
| C7 | WARN | value null or negative | count | 0 and 0 | 1,403 rows are exactly zero, kept |
| C8 | WARN | duplicate natural key | 0 | 0 | per-year singular test |
| C9 | NOTE | value whose current description differs from the validity-matched one | measured | 8.49% of all years | the headline |
| C10 | WARN | import codes absent from the dictionary | count | 0 | none to bucket |
| C11 | BLOCK | run log has an ok row for every year in the manifest | all | all 39 | no log, no claim |
| C12 | WARN | quantity zero with value above zero | count | 71,985,063, 38.65% | quantity is not used |
| C13 | NOTE | values are nominal CAD at customs valuation | documented | D-06 | no deflation |
| C14 | WARN | validity months that do not convert, the sentinel included | 0 | 0 | 999912 becomes 9999-12-31 |
