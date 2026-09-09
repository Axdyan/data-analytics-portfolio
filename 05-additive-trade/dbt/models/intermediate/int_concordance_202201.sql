-- The publisher's own map from the codes that ended in December 2021 to the codes that began in
-- January 2022, read from the committed CSV and joined to the dictionary at both ends. The
-- mechanical rule this project first planned to use, pair a retired code with the new codes in its
-- subheading or else its heading, is computed alongside as mechanical_relation, so the notebook can
-- say how often it would have been right rather than assume it. One row per published pair.
with pairs as (

    select distinct obsolete_hs10, new_hs10, source_file, source_url, checked_on
    from {{ ref('concordance_202201') }}

),

ending as (

    select hs10, desc_en, valid_from
    from {{ ref('int_hs10_validity') }}
    where valid_to = date '2021-12-31'

),

starting as (

    select hs10, desc_en, is_current
    from {{ ref('int_hs10_validity') }}
    where valid_from = date '2022-01-01'

),

fan_out as (

    select obsolete_hs10, count(*) as n_new_for_obsolete from pairs group by 1

),

fan_in as (

    select new_hs10, count(*) as n_obsolete_for_new from pairs group by 1

)

select
    p.obsolete_hs10 || '-' || p.new_hs10                                as pair_key,
    p.obsolete_hs10,
    e.desc_en                                                           as obsolete_desc_en,
    e.valid_from                                                        as obsolete_valid_from,
    e.hs10 is not null                                                  as obsolete_ends_2021_12,
    p.new_hs10,
    s.desc_en                                                           as new_desc_en,
    s.is_current                                                        as new_is_current,
    s.hs10 is not null                                                  as new_starts_2022_01,
    p.obsolete_hs10 = p.new_hs10                                        as same_code,
    case
        when p.obsolete_hs10 = p.new_hs10                               then 'same code'
        when left(p.obsolete_hs10, 6) = left(p.new_hs10, 6)             then 'same subheading'
        when left(p.obsolete_hs10, 4) = left(p.new_hs10, 4)             then 'same heading'
        when left(p.obsolete_hs10, 2) = left(p.new_hs10, 2)             then 'same chapter'
        else 'different chapter'
    end                                                                 as mechanical_relation,
    f.n_new_for_obsolete,
    g.n_obsolete_for_new,
    case
        when f.n_new_for_obsolete = 1 and g.n_obsolete_for_new = 1      then 'one to one'
        when f.n_new_for_obsolete > 1 and g.n_obsolete_for_new = 1      then 'split'
        when f.n_new_for_obsolete = 1 and g.n_obsolete_for_new > 1      then 'merge'
        else 'many to many'
    end                                                                 as mapping_type,
    'published statistical concordance'                                 as rule,
    'high'                                                              as confidence,
    p.source_file,
    p.source_url,
    p.checked_on
from pairs p
left join ending e on e.hs10 = p.obsolete_hs10
left join starting s on s.hs10 = p.new_hs10
left join fan_out f on f.obsolete_hs10 = p.obsolete_hs10
left join fan_in g on g.new_hs10 = p.new_hs10
