-- The fact at the source grain: one row per month, code, partner country, province and US
-- state, carrying the validity period key rather than the bare code. Incremental by year,
-- because a year is the unit the publisher republishes and the unit the backfill writes. A run
-- replaces the latest year already loaded and every year after it, which refreshes the partial
-- current year and adds new years, and it also takes any year present in the source but absent
-- from the table, which is how a backfill of earlier years gets in without a full refresh. A
-- full refresh rebuilds everything in one pass. Passing years as a variable rebuilds exactly
-- those, for a year the publisher revised.
{{ config(
    materialized = 'incremental',
    incremental_strategy = 'delete+insert',
    unique_key = 'year'
) }}

select
    year,
    ref_month,
    hs10,
    hs10_period_key,
    equijoin_status,
    partner_country,
    province,
    us_state,
    value_cad,
    quantity,
    uom,
    parquet_row
from {{ ref('int_imports_with_validity') }}

{% if var('years', none) is not none %}
where year in ({{ var('years') | join(', ') }})
{% elif is_incremental() %}
where year >= (select coalesce(max(year), 0) from {{ this }})
   or year not in (select distinct year from {{ this }})
{% endif %}
