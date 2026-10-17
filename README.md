# FCR-N Battery Simulator

Simulates a battery providing **FCR-N** (Frequency Containment Reserve – Normal) on the Nordic grid, using real 0.1 s frequency data from Fingrid. It covers the throughput, state of charge (SOC) and LER energy management (**NEM** and **AEM**) from the Nordic FCR technical requirements.

The site is one self-contained HTML page. It plots all 864,000 samples of a day (power, frequency and SOC), lets you change the battery and bid size, and recalculates everything in the browser.

## Quick start

```bash
pip install -r requirements.txt
# put a Fingrid daily CSV in data/ (see data/README.md), then:
python scripts/build_site.py data/2026-08/Taajuusdata2026-08-29.csv   # -> site/index.html
```

Open `site/index.html` in a browser. It needs internet access for the charting library (uPlot from jsDelivr) and fonts.

To analyse a whole month and find the worst day (no energy management):

```bash
python scripts/analyse_month.py data/2026-08 results/fcrn_daily_2026-08.csv --power 1 --energy 2
```

## Model

| Item | Assumption |
|---|---|
| FCR-N response | P = C × clip((50 − f) / 0.1 Hz, −1, 1); linear, full output at ±100 mHz, no deadband. Positive = discharge. |
| Battery | Rated power and energy set by the user; SOC limited to 0–100 %. |
| Losses | Round-trip efficiency (default 90 %) split evenly: √η on charge and on discharge. |
| Start | SOC set by the user (default 50 %) at 00:00. |
| Data cleaning | Values outside 49–51 Hz (0 Hz dropouts) and single-sample spikes (> 50 mHz from a 9-sample median) are removed and forward-filled. |

### Sizing check (Nordic FCR requirements v1.1, Table 10)

- Battery power ≥ **1.34 × C** (C = prequalified FCR-N capacity)
- Energy ≥ **1 h × C in each direction**, i.e. ≥ 2 h × C in total

### Energy management for LER units

Minutes left = stored energy ÷ C (discharge side) or free room ÷ C (charge side).

| | Switch on | Switch off | Behaviour |
|---|---|---|---|
| **NEM** | < 30 min left on either side | > 57.5 min | Allowed only while 49.9 < f < 50.1 Hz. Signal −1/0/+1, averaged over the last 300 s (1 s steps). P_NEM = 0.34 × C × average, added to the FCR-N response. |
| **AEM** | ≤ 5 min left on either side (any frequency) | > 10 min | FCR-N responds around the 5-minute average frequency instead of 50 Hz. The unit counts as unavailable. NEM keeps running in parallel. |

The thresholds come from Energinet's prequalification document, which sets out section 3.5 / Table 11 of the Nordic requirements. The Nordic TSOs say these values will be reviewed periodically, so check them against the latest ENTSO-E version.

## Results so far (August 2026, 1 MW / 2 MWh, C = 1 MW, no energy management)

- Worst day: **29 August**. Throughput 6.01 MWh (1.5 full cycles), with 4.07 MWh discharged and 1.94 MWh charged.
- Frequency was low for most of the day, so the battery ran empty at 10:04 and was unavailable for 3.8 h.
- With NEM + AEM on and a compliant bid (C = 0.74 MW), the battery never runs empty and never enters AEM. Its lowest SOC is 16 %.

Daily figures for the whole month are in `results/fcrn_daily_2026-08.csv`.

## Project layout

```
src/template.html        Page source (HTML/CSS/JS); data and date are injected at build time
src/vendor/uPlot.min.css uPlot stylesheet (inlined into the page)
scripts/build_site.py    CSV -> site/index.html (frequency embedded as base64 int16)
scripts/analyse_month.py Month-wide simulation and worst-day search
results/                 Analysis outputs
site/index.html          Built page (deployed to GitHub Pages)
data/                    Raw Fingrid CSVs (not committed)
```

## Publishing

On GitHub, go to **Settings → Pages → Source: GitHub Actions**. Each push to `main` that changes `site/` then deploys automatically through `.github/workflows/pages.yml`.

## Ideas to work on

- Day picker for the whole month, or uploading your own Fingrid CSV in the browser
- FCR-D up/down (deadband, ramp and the 0.2 × C NEM share)
- Hourly bid sizes and hours without a bid
- Revenue estimate from FCR-N capacity prices (Fingrid/Svenska kraftnät market data)
- Battery ageing / cycle cost per day
- Export results as CSV

## Sources

- ENTSO-E, *Technical Requirements for Frequency Containment Reserve Provision in the Nordic Synchronous Area*, v1.1, 28 March 2025 (section 3.5, Table 10)
- Energinet, *Prequalification of FCR-N and FCR-D* (NEM and AEM implementation)
- Fingrid open data, dataset 339: frequency, historical data (0.1 s)
