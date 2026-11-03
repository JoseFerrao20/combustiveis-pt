-- A última fotografia da DGEG (transform/models/reporting/rpt_stations_latest.sql), só com as
-- colunas que as páginas do Evidence usam (o número de postos e o dia): o Evidence descarrega
-- cada fonte inteira em todas as páginas. Os preços estão nas páginas leves (app/).
select distinct snapshot_date, station_id from read_parquet('../data/stations_latest.parquet')
