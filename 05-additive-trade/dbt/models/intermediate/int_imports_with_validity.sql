-- The temporal join, the technique this project exists to show. Every import row finds the
-- dictionary period whose validity range contains its reference month, not the period that
-- happens to be current today. A join on the code alone is the wrong answer being corrected,
-- and the equijoin_status column says, row by row, what that wrong answer would have done:
-- attached a different description, orphaned the row because the code has no current period,
-- or got it right by luck because the code never changed. The join is a left join so that a
-- code missing from the dictionary stays in the data as unmatched and can be counted.
{{ config(materialized='view') }}

select
    i.year,
    i.ref_month,
    i.hs10,
    d.hs10_period_key,
    d.version_no,
    d.desc_en,
    d.current_desc_en,
    d.meaning_changed,
    case
        when d.hs10_period_key is null            then 'unmatched'
        when d.current_desc_en is null            then 'no current period'
        when d.current_desc_en <> d.desc_en       then 'current description differs'
        else                                           'same'
    end                                                                         as equijoin_status,
    i.partner_country,
    i.province,
    i.us_state,
    i.value_cad,
    i.quantity,
    i.uom,
    i.parquet_row
from {{ ref('stg_cimt_imports') }} as i
left join {{ ref('int_hs10_validity') }} as d
    on  i.hs10 = d.hs10
    and i.ref_month between d.valid_from and d.valid_to
