-- The four small lookups in one typed table, since they share a layout and a job. The country
-- code field carries the two-letter code and a numeric code separated by a space; the province
-- field carries the number and the two-letter abbreviation. Each row keeps its validity range,
-- because provinces and countries were renamed too: Newfoundland became Newfoundland and
-- Labrador under the same code before the code itself changed.
with country as (
    select 'country' as lookup, split_part(code, ' ', 1) as code, split_part(code, ' ', 2) as code_number,
           valid_from, valid_to, desc_en, desc_fr, file_month, line_no
    from {{ source('raw', 'country_dictionary') }}
),
province as (
    select 'province' as lookup, split_part(code, ' ', 2) as code, split_part(code, ' ', 1) as code_number,
           valid_from, valid_to, desc_en, desc_fr, file_month, line_no
    from {{ source('raw', 'province_dictionary') }}
),
state as (
    select 'state' as lookup, code, null as code_number,
           valid_from, valid_to, desc_en, desc_fr, file_month, line_no
    from {{ source('raw', 'state_dictionary') }}
),
uom as (
    select 'uom' as lookup, code, null as code_number,
           valid_from, valid_to, desc_en, desc_fr, file_month, line_no
    from {{ source('raw', 'uom_dictionary') }}
),
unioned as (
    select * from country
    union all select * from province
    union all select * from state
    union all select * from uom
)
select
    lookup,
    code,
    code_number,
    cast(try_strptime(valid_from || '01', '%Y%m%d') as date)                   as valid_from,
    last_day(cast(try_strptime(valid_to || '01', '%Y%m%d') as date))           as valid_to,
    valid_to = '999912'                                                         as is_current,
    desc_en,
    desc_fr,
    file_month                                                                  as snapshot_month,
    line_no
from unioned
