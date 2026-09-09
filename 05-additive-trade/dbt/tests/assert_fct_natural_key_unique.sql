-- depends_on: {{ ref('fct_imports_monthly') }}
-- C8. The natural key of the fact is the month, the code, the partner country, the province and
-- the US state. A duplicate would mean the publisher's file carries two rows for one cell, or
-- that an incremental run loaded a year twice. Grouping all hundred and eighty-odd million rows
-- at once needs a hash table far larger than the memory this machine can spare, so the test is
-- one aggregate per year, each of which fits, and the years come from the table itself at run
-- time. The first line tells dbt about the dependency, since the reference below sits inside a
-- block that only runs at execution.
{% if execute %}
    {% set year_rows = run_query("select distinct year from " ~ ref('fct_imports_monthly') ~ " order by year") %}
    {% set years = year_rows.columns[0].values() %}
{% else %}
    {% set years = [] %}
{% endif %}

{% for y in years %}
select ref_month, hs10, partner_country, province, us_state, count(*) as n
from {{ ref('fct_imports_monthly') }}
where year = {{ y }}
group by ref_month, hs10, partner_country, province, us_state
having count(*) > 1
{% if not loop.last %}
union all
{% endif %}
{% endfor %}
{% if not years %}
select null as ref_month, null as hs10, null as partner_country, null as province, null as us_state, 0 as n
where false
{% endif %}
