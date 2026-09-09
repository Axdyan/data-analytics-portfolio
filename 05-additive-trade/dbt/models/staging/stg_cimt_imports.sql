-- Typed and renamed, one row per source row, nothing dropped. Every column in the Parquet is
-- text, so the casts happen here where a failure is visible: a value that will not cast comes
-- through as null next to its raw text, and a test counts those rather than letting a type guess
-- swallow them. The state column is blank on every partner but the United States, so blank
-- becomes null. parquet_row is the row's position inside its year's file, the trace back to the
-- source.
with source as (

    select * from {{ source('raw', 'cimt_imports') }}

)

select
    cast(year as integer)                                                       as year,
    cast(try_strptime("YearMonth/AnnéeMois", '%Y%m') as date)                  as ref_month,
    "YearMonth/AnnéeMois"                                                       as ref_month_raw,
    "HS10"                                                                      as hs10,
    "Country/Pays"                                                              as partner_country,
    "Province"                                                                  as province,
    nullif("State/État", '')                                                    as us_state,
    try_cast("Value/Valeur" as bigint)                                          as value_cad,
    "Value/Valeur"                                                              as value_raw,
    try_cast("Quantity/Quantité" as bigint)                                     as quantity,
    "Quantity/Quantité"                                                         as quantity_raw,
    nullif("Unit of Measure/Unité de Mesure", '')                               as uom,
    file_row_number                                                             as parquet_row
from source
