# Data

Raw frequency files are not committed (about 28 MB per day, 860 MB per month).

1. Download a month from Fingrid open data, dataset 339 "Frequency – historical data":
   https://data.fingrid.fi/en/datasets/339
2. Unpack the `.7z` into this folder, e.g. `data/2026-08/Taajuusdata2026-08-29.csv`.

Each CSV has two columns, `Time` (local time, 0.1 s steps) and `Value` (Hz).
