-- The dimension a naive model would build: one row per code with whatever it means today. It
-- exists so the dashboard can show the join on the code alone beside the temporal join, and it
-- is missing every code that has no open period, which is the second way that join loses value.
select
    hs10,
    hs2,
    hs4,
    hs6,
    desc_en                                                                     as current_desc_en,
    desc_fr                                                                     as current_desc_fr,
    valid_from                                                                  as current_since,
    n_versions,
    code_ever_changed_meaning
from {{ ref('int_hs10_validity') }}
where is_current
