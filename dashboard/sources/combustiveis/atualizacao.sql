-- O manifesto da última ingestão (combustiveis ingest): quando se descarregou o boletim.
select
    cast(downloaded_at as timestamp) as downloaded_at,
    cast(latest_week as date) as latest_week
from read_json_auto('../data/landing/manifest.json')
