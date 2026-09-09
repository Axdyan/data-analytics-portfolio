-- C7. Import value must not be negative. Nulls are counted separately by the not_null warning on
-- the staging model; this returns the rows that carry a negative number.
{{ config(severity = 'warn') }}

select year, ref_month, hs10, partner_country, province, us_state, value_cad
from {{ ref('stg_cimt_imports') }}
where value_cad < 0
