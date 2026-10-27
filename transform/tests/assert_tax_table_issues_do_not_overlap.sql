-- Cada período do seed known_tax_table_issues começa antes de acabar e não se sobrepõe a outro
-- do mesmo país e produto (senão, uma semana teria duas explicações).
select a.*
from {{ ref('known_tax_table_issues') }} as a
left join {{ ref('known_tax_table_issues') }} as b
    on b.country_code = a.country_code
    and b.product = a.product
    and b.valid_from > a.valid_from
    and b.valid_from <= a.valid_to
where a.valid_from > a.valid_to
    or b.country_code is not null
