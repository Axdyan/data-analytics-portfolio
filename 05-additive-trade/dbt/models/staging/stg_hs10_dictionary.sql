-- The dictionary typed: the YYYYMM months become the first day of the opening month and the
-- last day of the closing month, so a reference month falls inside a period with a plain
-- BETWEEN. The 999912 sentinel that marks a still-open period converts to 9999-12-31 by the same
-- arithmetic and is never null, which is the whole point: a null there would drop every current
-- code from the join. N/A in the unit column is the publisher's way of saying no unit, so it is
-- null here.
select
    code                                                                        as hs10,
    cast(try_strptime(valid_from || '01', '%Y%m%d') as date)                   as valid_from,
    last_day(cast(try_strptime(valid_to || '01', '%Y%m%d') as date))           as valid_to,
    valid_to = '999912'                                                         as is_current,
    nullif(uom, 'N/A')                                                          as uom,
    desc_en,
    desc_fr,
    file_month                                                                  as snapshot_month,
    line_no,
    source_zip
from {{ source('raw', 'hs10_dictionary') }}
