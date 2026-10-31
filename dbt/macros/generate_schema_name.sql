{#
  Sem este macro, o dbt criaria schemas como "analytics_staging" e
  "analytics_marts". Aqui usamos o nome do schema customizado direto,
  que é o padrão que a maioria dos times adota.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
