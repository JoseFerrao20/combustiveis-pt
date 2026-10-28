-- A última fotografia da DGEG, exportada pelo dbt (transform/models/reporting/rpt_stations_latest.sql).
select * from read_parquet('../data/stations_latest.parquet')
