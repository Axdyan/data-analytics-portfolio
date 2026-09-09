-- One row per month from the first month in the data to the last, so the dashboard's time axis
-- is a date and the period boundaries the dictionary uses land on real months.
with bounds as (

    select min(ref_month) as first_month, max(ref_month) as last_month
    from {{ ref('stg_cimt_imports') }}

),

months as (

    select unnest(generate_series(first_month, last_month, interval 1 month))::date as ref_month
    from bounds

)

select
    ref_month,
    year(ref_month)                                                             as year,
    month(ref_month)                                                            as month_no,
    strftime(ref_month, '%b')                                                   as month_name,
    'Q' || quarter(ref_month)                                                   as quarter,
    strftime(ref_month, '%Y-%m')                                                as year_month,
    ref_month >= date '2022-01-01'                                              as from_2022
from months
