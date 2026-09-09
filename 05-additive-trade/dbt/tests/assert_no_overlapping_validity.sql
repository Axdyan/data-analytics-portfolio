-- C2. Two periods of the same code must never overlap, or the temporal join would match a month
-- to both and duplicate the row. Returns the periods that start on or before the previous one ended.
with ordered as (

    select
        hs10,
        valid_from,
        valid_to,
        lag(valid_to) over (partition by hs10 order by valid_from) as prior_valid_to
    from {{ ref('stg_hs10_dictionary') }}

)

select *
from ordered
where prior_valid_to is not null
  and valid_from <= prior_valid_to
