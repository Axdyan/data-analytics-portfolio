-- C10. Import rows whose code is missing from the dictionary for their month. A warning rather
-- than a failure: they stay in the fact as unmatched and are counted in the corruption mart.
{{ config(severity = 'warn') }}

select
    year,
    hs10,
    count(*)        as rows_unmatched,
    sum(value_cad)  as value_unmatched
from {{ ref('int_imports_with_validity') }}
where hs10_period_key is null
group by year, hs10
