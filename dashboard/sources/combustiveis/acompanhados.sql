-- Os postos acompanhados, por dia e combustível (transform/models/reporting/rpt_tracked_stations_daily.sql).
select * from read_parquet('../data/tracked_stations_daily.parquet')
