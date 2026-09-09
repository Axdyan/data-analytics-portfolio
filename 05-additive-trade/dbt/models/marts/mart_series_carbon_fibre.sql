-- Carbon fibre month by month from 1988, with the regime the dictionary puts each month in. The
-- windows and their labels come from the series definitions, read straight off the dictionary
-- rows: two stretches with no carbon fibre code at all, one clean code, thirteen years of the same
-- code shared with refractory brick, and three codes from 2022. Value is null in a month with no
-- code, because there is nothing to sum, and zero in a coded month with no imports. The epoxide
-- sheet code that ended in 2011 is a second series with the same treatment.
with windows as (

    select
        series_key,
        role,
        hs10,
        regime,
        cast(window_from as date)                                       as window_from,
        cast(window_to as date)                                         as window_to
    from {{ ref('series_definitions') }}
    where series_key in ('carbon_fibre_articles', 'carbon_fibre_epoxide_sheet')

),

months as (

    select ref_month from {{ ref('dim_date') }}

),

month_regime as (

    select distinct w.series_key, d.ref_month, w.regime, w.window_from as regime_from
    from windows w
    join months d on d.ref_month between w.window_from and w.window_to

),

coded as (

    select w.series_key, d.ref_month, w.hs10
    from windows w
    join months d on d.ref_month between w.window_from and w.window_to
    where w.hs10 is not null

),

fact as (

    select hs10, ref_month, sum(value_cad) as value_cad, count(*) as n_rows
    from {{ ref('fct_imports_monthly') }}
    where hs10 in (select hs10 from windows where hs10 is not null)
    group by 1, 2

),

summed as (

    select
        c.series_key,
        c.ref_month,
        count(*)                                                        as n_codes,
        string_agg(c.hs10, ' ' order by c.hs10)                         as codes,
        sum(coalesce(f.value_cad, 0))                                   as value_cad,
        sum(coalesce(f.n_rows, 0))                                      as n_rows
    from coded c
    left join fact f on f.hs10 = c.hs10 and f.ref_month = c.ref_month
    group by 1, 2

)

select
    r.series_key,
    r.ref_month,
    r.regime,
    r.regime_from,
    s.n_codes is not null                                               as separately_coded,
    coalesce(s.n_codes, 0)                                              as n_codes,
    s.codes,
    s.value_cad,
    s.n_rows,
    r.series_key || '|' || strftime(r.ref_month, '%Y-%m')               as series_month_key
from month_regime r
left join summed s on s.series_key = r.series_key and s.ref_month = r.ref_month
order by r.series_key, r.ref_month
