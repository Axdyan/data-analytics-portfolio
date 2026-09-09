-- One row per code within each lookup, carrying the most recent description, so the dashboard
-- relationships are one to many. The province NF and the province NL are both here because both
-- appear in the fact table across the years; the validity ranges stay in stg_lookups for anyone
-- who needs them.
with ranked as (

    select
        *,
        row_number() over (partition by lookup, code order by valid_from desc)  as recency
    from {{ ref('stg_lookups') }}

)

select
    lookup,
    code,
    code_number,
    desc_en,
    desc_fr,
    valid_from                                                                  as latest_valid_from,
    valid_to                                                                    as latest_valid_to,
    is_current
from ranked
where recency = 1
