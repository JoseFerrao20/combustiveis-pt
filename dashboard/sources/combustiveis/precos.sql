-- Exportado pelo dbt (transform/models/reporting/rpt_road_fuel_prices.sql), em € por litro.
select * from read_parquet('../data/road_fuel_prices.parquet')
