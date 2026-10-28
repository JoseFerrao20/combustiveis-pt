-- Médias diárias da DGEG, exportadas pelo dbt (transform/models/reporting/rpt_station_prices_daily.sql).
select * from read_parquet('../data/station_prices_daily.parquet')
