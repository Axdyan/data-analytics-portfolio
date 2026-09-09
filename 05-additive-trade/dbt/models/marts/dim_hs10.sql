-- The validity dimension: one row per code and period, keyed on the code plus its opening month.
-- It has the shape of a type 2 slowly changing dimension, and the ranges come from the
-- publisher's own dictionary rather than from snapshots taken by this project, which is stated
-- here because the two are not the same claim.
select
    hs10_period_key,
    hs10,
    hs2,
    hs4,
    hs6,
    valid_from,
    valid_to,
    is_current,
    version_no,
    n_versions,
    uom,
    desc_en,
    desc_fr,
    prior_desc_en,
    meaning_changed,
    code_ever_changed_meaning,
    current_desc_en,
    differs_from_current,
    snapshot_month
from {{ ref('int_hs10_validity') }}
