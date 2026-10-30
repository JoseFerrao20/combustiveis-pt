-- As cotações diárias do FRED, tal como vieram (só os dias com cotação).
select series, day, value
from {{ source('fred', 'markets') }}
