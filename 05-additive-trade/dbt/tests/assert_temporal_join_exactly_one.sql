-- C5. Every import row must match exactly one dictionary period, so the joined view must hold
-- exactly as many rows as the staging view. Comparing the two counts costs one pass each and
-- needs no hash of a hundred million keys; the overlap test above is what guarantees the
-- property, and this is the check that it held on the data.
with counts as (

    select
        (select count(*) from {{ ref('stg_cimt_imports') }})        as rows_staged,
        (select count(*) from {{ ref('int_imports_with_validity') }}) as rows_joined

)

select *
from counts
where rows_staged <> rows_joined
