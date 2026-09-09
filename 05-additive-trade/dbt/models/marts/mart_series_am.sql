-- Monthly national import value for the additive manufacturing series: each recipient and donor
-- code on its own, then three baskets. The recipient basket is the nine codes the heading opened
-- with in 2022. The donor basket is every 2021 code the publisher's concordance points at one of
-- the nine, so its fall at the break is where the goods came from. Combined is both together, the
-- one basket whose contents do not change when the heading opens. A basket starts at the first
-- month every member code exists, so it is never a partial set; recipients count as zero before
-- 2022 in the combined basket because their goods were inside the donors then. A month with no
-- imports is a zero row, not a missing one.
with members as (

    select
        series_key,
        role,
        hs10,
        cast(window_from as date)                                       as window_from,
        cast(window_to as date)                                         as window_to
    from {{ ref('series_definitions') }}
    where series_key in ('am_recipients', 'am_donors') and hs10 is not null

),

months as (

    select ref_month from {{ ref('dim_date') }}

),

fact as (

    select hs10, ref_month, sum(value_cad) as value_cad, count(*) as n_rows
    from {{ ref('fct_imports_monthly') }}
    where hs10 in (select hs10 from members)
    group by 1, 2

),

code_level as (

    select
        m.role || ':' || m.hs10                                         as series_key,
        m.role,
        m.hs10,
        d.ref_month,
        coalesce(f.value_cad, 0)                                        as value_cad,
        coalesce(f.n_rows, 0)                                           as n_rows,
        case when f.value_cad > 0 then 1 else 0 end                     as n_codes_with_value
    from members m
    join months d on d.ref_month between m.window_from and m.window_to
    left join fact f on f.hs10 = m.hs10 and f.ref_month = d.ref_month

),

basket_start as (

    select
        max(case when role = 'recipient' then window_from end)          as recipients_from,
        max(case when role = 'donor' then window_from end)              as donors_from
    from members

),

baskets as (

    select 'recipients' as series_key, 'recipient' as role, c.ref_month,
           sum(c.value_cad) as value_cad, sum(c.n_rows) as n_rows,
           sum(c.n_codes_with_value) as n_codes_with_value, count(*) as n_members
    from code_level c, basket_start b
    where c.role = 'recipient' and c.ref_month >= b.recipients_from
    group by c.ref_month

    union all

    select 'donors', 'donor', c.ref_month,
           sum(c.value_cad), sum(c.n_rows), sum(c.n_codes_with_value), count(*)
    from code_level c, basket_start b
    where c.role = 'donor' and c.ref_month >= b.donors_from
    group by c.ref_month

    union all

    select 'combined', 'both', c.ref_month,
           sum(c.value_cad), sum(c.n_rows), sum(c.n_codes_with_value), count(*)
    from code_level c, basket_start b
    where c.ref_month >= b.donors_from
    group by c.ref_month

)

select
    series_key,
    'code'                                                              as series_group,
    role,
    hs10,
    ref_month,
    value_cad,
    n_rows,
    n_codes_with_value,
    1                                                                   as n_members,
    series_key || '|' || strftime(ref_month, '%Y-%m')                   as series_month_key
from code_level

union all

select
    series_key,
    'basket',
    role,
    null,
    ref_month,
    value_cad,
    n_rows,
    n_codes_with_value,
    n_members,
    series_key || '|' || strftime(ref_month, '%Y-%m')
from baskets

order by series_key, ref_month
