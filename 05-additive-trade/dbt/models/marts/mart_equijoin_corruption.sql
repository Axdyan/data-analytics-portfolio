-- What a join on the code alone would have done to the numbers, by year. Every row of the fact
-- is in exactly one bucket: the naive join attaches the same description the temporal join does,
-- attaches a different one, finds no current period and orphans the row, or the code is missing
-- from the dictionary altogether. The value in the second bucket is the headline corruption
-- figure, C9 in the assertion suite; the third bucket is value a naive model silently loses.
with by_year as (

    select
        year,
        count(*)                                                                                 as rows_total,
        sum(value_cad)                                                                           as value_total,
        sum(case when equijoin_status = 'same' then value_cad else 0 end)                        as value_same,
        sum(case when equijoin_status = 'current description differs' then value_cad else 0 end) as value_misdescribed,
        sum(case when equijoin_status = 'no current period' then value_cad else 0 end)           as value_orphaned,
        sum(case when equijoin_status = 'unmatched' then value_cad else 0 end)                   as value_unmatched,
        count(*) filter (where equijoin_status = 'current description differs')                  as rows_misdescribed,
        count(*) filter (where equijoin_status = 'no current period')                            as rows_orphaned,
        count(*) filter (where equijoin_status = 'unmatched')                                    as rows_unmatched,
        count(distinct case when equijoin_status = 'current description differs' then hs10 end)  as codes_misdescribed
    from {{ ref('fct_imports_monthly') }}
    group by year

)

select
    *,
    round(100.0 * value_misdescribed / value_total, 2)                                          as pct_misdescribed,
    round(100.0 * value_orphaned / value_total, 2)                                              as pct_orphaned,
    round(100.0 * (value_misdescribed + value_orphaned) / value_total, 2)                       as pct_wrong_under_equijoin
from by_year
order by year
