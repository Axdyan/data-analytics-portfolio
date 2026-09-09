-- Every code named in the series definitions must exist in the dictionary for the whole window
-- claimed for it, or a series would carry months the code did not cover. And a carbon fibre
-- window is a claim about what the code meant, so it must not span a change of description.
-- Donor windows are allowed to, since their narrowing at the break is the point. A row comes back
-- for any month without a period, and one per window that spans two descriptions.
with defs as (

    select
        series_key,
        role,
        hs10,
        regime,
        cast(window_from as date)                                       as window_from,
        cast(window_to as date)                                         as window_to
    from {{ ref('series_definitions') }}
    where hs10 is not null

),

months as (

    select ref_month from {{ ref('dim_date') }}

),

claimed as (

    select d.series_key, d.role, d.hs10, d.regime, d.window_from, m.ref_month
    from defs d
    join months m on m.ref_month between d.window_from and d.window_to

),

matched as (

    select c.*, v.desc_en
    from claimed c
    left join {{ ref('int_hs10_validity') }} v
        on v.hs10 = c.hs10 and c.ref_month between v.valid_from and v.valid_to

)

select 'month without a dictionary period' as problem, series_key, hs10, regime, ref_month as at_month
from matched
where desc_en is null

union all

select 'window spans more than one description', series_key, hs10, regime, window_from
from matched
where role like 'carbon fibre%'
group by series_key, hs10, regime, window_from
having count(distinct desc_en) > 1
