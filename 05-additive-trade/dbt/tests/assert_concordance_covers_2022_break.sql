-- The published concordance has to account for every code the dictionary closes in December 2021
-- and every code it opens in January 2022, or a series built on it could be missing a donor.
-- Rows returned are codes the concordance does not mention, either way round.
with ending as (

    select hs10 from {{ ref('int_hs10_validity') }} where valid_to = date '2021-12-31'

),

starting as (

    select hs10 from {{ ref('int_hs10_validity') }} where valid_from = date '2022-01-01'

),

conc as (

    select obsolete_hs10, new_hs10 from {{ ref('concordance_202201') }}

)

select 'ends 2021-12 but not listed as obsolete' as problem, hs10
from ending
where hs10 not in (select obsolete_hs10 from conc)

union all

select 'starts 2022-01 but not listed as new', hs10
from starting
where hs10 not in (select new_hs10 from conc)
