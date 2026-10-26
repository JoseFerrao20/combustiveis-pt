{% test unique_combination(model, columns) %}
-- Falha com as combinações repetidas (como o unique, mas para várias colunas).
select {{ columns | join(', ') }}, count(*) as repetitions
from {{ model }}
group by all
having count(*) > 1
{% endtest %}
