-- The validity dimension in the making: one row per code and period, numbered in order, with
-- what the code meant in its previous period and a flag for whether the meaning changed. The
-- period key is the code plus its opening month, which is what the fact table carries instead
-- of the bare code. current_desc_en is the description a join on the code alone would attach
-- today, kept on every period so the gap between the two is a column, not a calculation.
with periods as (

    select
        hs10,
        valid_from,
        valid_to,
        is_current,
        uom,
        desc_en,
        desc_fr,
        snapshot_month,
        line_no,
        row_number() over (partition by hs10 order by valid_from)                          as version_no,
        count(*) over (partition by hs10)                                                   as n_versions,
        lag(desc_en) over (partition by hs10 order by valid_from)                           as prior_desc_en,
        lag(valid_to) over (partition by hs10 order by valid_from)                          as prior_valid_to,
        max(case when is_current then desc_en end) over (partition by hs10)                 as current_desc_en
    from {{ ref('stg_hs10_dictionary') }}

),

flagged as (

    select
        *,
        prior_desc_en is not null and prior_desc_en <> desc_en                              as meaning_changed,
        max(case when prior_desc_en is not null and prior_desc_en <> desc_en then 1 else 0 end)
            over (partition by hs10) = 1                                                    as code_ever_changed_meaning
    from periods

)

select
    hs10 || '-' || strftime(valid_from, '%Y%m')                                             as hs10_period_key,
    hs10,
    left(hs10, 2)                                                                           as hs2,
    left(hs10, 4)                                                                           as hs4,
    left(hs10, 6)                                                                           as hs6,
    valid_from,
    valid_to,
    is_current,
    version_no,
    n_versions,
    uom,
    desc_en,
    desc_fr,
    prior_desc_en,
    prior_valid_to,
    meaning_changed,
    code_ever_changed_meaning,
    current_desc_en,
    current_desc_en is not null and current_desc_en <> desc_en                              as differs_from_current,
    snapshot_month,
    line_no
from flagged
