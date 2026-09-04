# Pitfalls in this dataset

Sixteen places where the obvious code is wrong against this file. Each one was
written the obvious way first, and each one either failed loudly or, worse,
returned a plausible number. They are recorded because most of them are invisible
in a code review: the query parses, runs, and gives you something that looks like
an answer.

The ten marked (silent) are the dangerous ones. Nothing raises, nothing looks
odd, and the number is wrong.

---

## 1. The download needs a User-Agent

The gateway refuses the default `python-requests` string with a 403 and accepts
anything else. Set the header explicitly. Fails loudly, but the error tells you
nothing about the cause.

## 2. Sixteen of twenty column-name guesses were wrong

The file ships 91 columns, most doubled into `-eng` and `-fra`. Guessing header
names from documentation does not work. Two that matter:

- The value column is `totalContractValue-valeurTotaleContrat`, not
  `contractValue`.
- `contractingEntityName-nomEntitContractante-eng` is missing the `e` on
  `Entite` **in the source itself**, so the rename map has to carry the typo.

Read the actual header row before writing a rename map.

## 3. Crosswalk cells that overwrite their own reviewed input (silent)

A crosswalk that is rebuilt from the data on every run will destroy the hand
research it exists to hold, the first time someone runs the notebook from the top.

Here it blanked the country crosswalk, and the downstream borrow rule then
invented countries for 1,760 rows without erroring. The reviewed file went from
one row to 1,760 and nothing said so. Every crosswalk must merge: reviewed values
win, new values arrive blank, and a blocking assertion catches anything uncovered.
The decision log has the measurement.

## 4. Blank means empty string, not null (silent)

Blank countries and blank end users are empty strings. `COALESCE(col, '(blank)')`
matches none of them and produces a join that silently drops rows. The test has to
be `NULLIF(TRIM(col), '') IS NULL`.

This one appears twice, in the country coverage assertion and again in the
end-user key on the amendment fact, where it would have quietly dropped rows on
the Power BI export.

## 5. The stop list has to include LIMITEE and LIMITE (silent)

Normalising supplier names by stripping trailing corporate tokens works, but the
list must come from the file's own trailing tokens rather than a generic English
one. Without the French forms, the largest defence supplier in the file splits
into two suppliers and drops out of the top of every ranking.

Names with no Latin characters also need an empty-key fallback, or they all
collapse onto one key.

## 6. The defence subset is a substring match, not an equality test

`IN ('Department of National Defence')` matches 374 rows. The correct `LIKE`
across DND and DRDC matches 4,229. One cell can list up to 25 end-user bodies
separated by slashes, so equality only catches rows where defence appears alone.

## 7. UNSPSC codes are starred and newline separated (silent)

The field holds up to 289 characters, several codes per cell, each prefixed with
an asterisk and separated by newlines. `substr(unspsc_code, 1, 4)` returns `*781`,
which is an asterisk and three digits. It is not a UNSPSC family, it groups
without complaint, and it silently ignores every code after the first.

Split on the newline and strip the stars first. `ltrim` rather than a regex, so
there is no escaping to get wrong.

## 8. Assertions that do not actually block

An assertion helper that classifies a rule as BLOCK and then carries on is
decoration. It has to raise. It also needs a per-rule tolerance, because two rules
here have known and accepted failures: the load rejects, and one genuine negative
contract value.

## 9. Hardcoded scope thresholds go stale on the next pull

Writing `LIMIT 40` for "the suppliers covering 80% of value" means the scope stops
meaning 80% the moment the distribution shifts. The measured line is 28 on this
pull. Derive it with a running share so it stays true. Same applies to how far
down the UNSPSC list to generate class rows.

## 10. Deriving a family from the raw code field (silent)

The same trap as 7, one layer up. Building the UNSPSC dimension with
`substr(raw_code, 1, 4)` produces asterisk-prefixed keys that join to nothing, so
every code falls through to the default segment and the segmentation looks
uniformly uninteresting rather than broken.

The dimension has to be keyed on the raw string, because that is what the fact
table carries, while family and class are derived from the first extracted code.

## 11. Lagging a denormalised column returns zero forever (silent)

`LAG` over `totalContractValue` partitioned by contract returns a delta of exactly
0 on all 4,314 amended contracts, because the total is repeated unchanged on every
amendment row. The window function is correct and the answer is meaningless.

`contractAmount` is the column that varies at amendment grain. Lag both and print
them side by side: the column of zeros is the evidence that the total is repeated, not a bug to
hide.

## 12. UNSPSC families are containers, not categories

A family label taken as `MIN(description)` is the alphabetically first description
in that family, which reads like a name and is not one. Family 7818 labels itself
"Aircraft fixed wing airframe heavy maintenance service" and also contains heavy
truck repair and ship refits. Family 2513 labels itself "Aircraft" and contains
the entire UAV fleet.

Measure the value split inside a family before tagging it. Here the contamination
turned out to be immaterial at 0.3%, but the same check is what found that the
uncrewed capability was about to be absorbed into aerospace and disappear. The decision log has the measurement.

## 13. contractAmount means different things on different contracts (silent)

The amendment-grain value column has no consistent semantic. Tested against the
contract total across every amended contract with no missing amounts, 39.4% behave
as an increment per amendment, 4.3% as a restatement of the contract, and 39.9%
match neither. That last group carries 69.9% of the value.

There is no correct way to aggregate it. A sum of amendment-to-amendment changes
runs fine and returns a large, confident, meaningless number. The only honest
output is that the column cannot be used for totals. The decision log has the measurement.

## 14. A null join key drops rows through every inner join (silent)

One supplier legal name is null. The deterministic name key of a null is null,
and a join on a null key matches nothing, so the row fell out of the supplier
dimension, both marts and the export, and every contract count downstream was
one short. Nothing raised, and the value figures were untouched because the row
is a $0 award, so nothing looked wrong.

It was caught by reconciling the export against its source table and finding
one more dropped row than the quarantine explained. Blank keys now get an
explicit `(blank)` value, the way blank countries and end users already did.
Any key that a join depends on needs the same treatment, or the join needs a
reconciliation that would notice. The decision log has the measurement.

## 15. The rename map went stale against a live publisher (silent)

The map of raw headers to short names was written from documentation of the
file as it stood before the publisher restructured it in spring 2026. The
restructuring added three columns, `amendmentType`, `instrumentType` and
`amendmentDate`, and the notebook ran cleanly without them for the whole build,
because a rename map only fails on a header it names and cannot find. It does
not fail on a header it never heard of.

Those three columns turned out to explain the unclassified segment, the
zero-value rows and most of the unexplained amendment value. Reading the header
row once (pitfall 2) is necessary and not sufficient. Against a source that
refreshes, diff the live header against the map on every run and read the
publisher's change notes when the column count moves. The decision log has the measurement.

## 16. The file calls every row a contract, and a third of them are not (silent)

4,239 rows at contract grain are standing offers or supply arrangements, which
are offers to supply at a price rather than awards of money. They sit at the
same grain as contracts, usually with a $0 total, and nothing in the value or
key columns distinguishes them. Every contract count in the file includes them,
and so did every count in this project until the instrument type was read.

They carry 7.7% of defence value and are almost all Canadian by address, so
their effect on the headline reading is under two points. It is still a
definition the reader has to be told about. The decision log has the measurement.

---

## The shape of it

Ten of the sixteen are silent. The recurring pattern is a field whose type or
grain is not what its name implies: a value column at the wrong grain, a code
field holding a list, a blank that is a string, a family that is a container,
a null where a key should be, an offer where a contract should be. In
every case the SQL is valid and the output is a number.

The defence against this is not more careful reading. It is measuring the thing
before building on it, which is what most of the assertion suite and several
otherwise pointless-looking cells in the notebook are actually for.
