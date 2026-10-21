# FCR Battery Simulator

Simulates a battery providing **FCR-N** and **FCR-D up/down** (Frequency Containment Reserves) on the Nordic grid, alone or together on one battery, using real 0.1 s frequency data from Fingrid. It covers the throughput, state of charge (SOC) and LER energy management (**NEM** and **AEM**) from the Nordic FCR technical requirements.

The site is one self-contained HTML page. It plots all 864,000 samples of a day (power, frequency and SOC), lets you pick products, split battery power between FCR-N and FCR-D, change the battery and bid sizes, and recalculates everything in the browser.

## Features

- **Load your own data**: pick one or more Fingrid daily CSVs in the browser. They are cleaned the same way as `scripts/build_site.py` and added to the Day list. Nothing is uploaded.
- **Products**: FCR-N, FCR-D up and FCR-D down, alone or combined, with a slider that splits battery power between FCR-N and FCR-D
- **Charts** (0.1 s, zoomable, linked): total power with separate FCR-N, FCR-D and NEM lines; frequency with the FCR-N band and FCR-D zones marked (optionally the full 49.5–50.5 Hz range); SOC with the SOC points used by FCR-N, used by FCR-D, restored by NEM, and lost (losses and limits) on a second axis. Every line can be hidden.
- **Scenarios**: save named settings in the browser, load or delete them, and import settings from an exported `.json`
- **Export**: results as CSV at 1 s (averaged power and frequency, end-of-second SOC) or the full 0.1 s resolution, plus a summary `.json` holding the settings and all results. On claude.ai this uses the page's download capability; when self-hosted it is a normal browser download.

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
| FCR-N response | P = C_N × clip((50 − f) / 0.1 Hz, −1, 1); linear, full output at ±100 mHz, no deadband. Positive = discharge. |
| FCR-D up / down | Static linear response: up from 49.9 Hz to full C_D↑ at 49.5 Hz; down from 50.1 Hz to full C_D↓ at 50.5 Hz. The dynamic ramp requirement is not modelled. |
| Combined bids | Responses are added and the total is limited to the battery's rated power. |
| Battery | Rated power and energy set by the user; SOC limited to 0–100 %. |
| Losses | Round-trip efficiency (default 90 %) split evenly: √η on charge and on discharge. |
| Start | SOC set by the user (default 50 %) at 00:00. |
| Data cleaning | Values outside 49–51 Hz (0 Hz dropouts) and single-sample spikes (> 50 mHz from a 9-sample median) are removed and forward-filled. |

### Sizing check (Nordic FCR requirements v1.1, Table 10)

- Power up ≥ **1.34 C_N + C_D↑ + 0.2 C_D↓**; power down ≥ **1.34 C_N + C_D↓ + 0.2 C_D↑**
- Energy: **1 h × C_N** in each direction for FCR-N, and **20 min × C_D** in its own direction for FCR-D
- For combined bids the requirements are added up (*assumption*: the source does not spell out combined bids)

### Power split

The slider gives a share *s* of battery power P to FCR-N: C_N = s·P / 1.34, and the rest goes to FCR-D: C_D = (1 − s)·P / 1.2 when both directions are bid (or / 1.0 for one direction, also checked against the opposite-direction NEM reservation). If the combined energy need exceeds the battery, all capacities are scaled down together. You can then edit each capacity by hand.

### Energy management for LER units

Minutes left = energy available ÷ C. Each product's 20-minute FCR-D energy is held back first, and FCR-N's thresholds only count the energy above it (*assumption* for sharing one reservoir).

| | Switch on | Switch off | Behaviour |
|---|---|---|---|
| **FCR-N NEM** | < 30 min left on either side | > 57.5 min | P = 0.34 × C_N × NEM_current |
| **FCR-D NEM** | < 20 min left in its direction | > 20 min | P = 0.2 × C_D × NEM_current, restoring the direction FCR-D uses |
| **AEM** (each product) | ≤ 5 min left (any frequency) | > 10 min | The product responds around the 5-minute average frequency instead of 50 Hz and counts as unavailable. NEM keeps running in parallel. |

NEM only runs while 49.9 < f < 50.1 Hz. Its signal (−1/0/+1) is averaged over the last 300 s at 1 s steps (NEM_current).

The thresholds come from Energinet's prequalification document, which sets out section 3.5 / Table 11 of the Nordic requirements. The Nordic TSOs say these values will be reviewed periodically, so check them against the latest ENTSO-E version.

## Results so far (August 2026, 1 MW / 2 MWh)

FCR-N only, C = 1 MW, no energy management:

- Worst day: **29 August**. Throughput 6.01 MWh (1.5 full cycles), with 4.07 MWh discharged and 1.94 MWh charged.
- Frequency was low for most of the day, so the battery ran empty at 10:04 and was unavailable for 3.8 h.
- With NEM + AEM on and a compliant bid (C = 0.74 MW), the battery never runs empty and never enters AEM. Its lowest SOC is 16 %.

29 August, NEM + AEM on:

| Split (FCR-N / FCR-D) | C_N / C_D↑ / C_D↓ (MW) | Throughput | FCR-D active | SOC range | SOC at midnight |
|---|---|---|---|---|---|
| 100 / 0 | 0.74 / – / – | 4.31 MWh | – | 16–50 % | 35 % |
| 80 / 20 | 0.59 / 0.16 / 0.16 | 3.47 MWh | 4.5 min | 17–50 % | 31 % |
| 50 / 50 | 0.37 / 0.41 / 0.41 | 2.36 MWh | 4.5 min | 14–50 % | 30 % |
| 0 / 100 | – / 0.83 / 0.83 | 2 kWh | 4.5 min | 50 % | 50 % |

Frequency only dropped below 49.9 Hz for 4.5 minutes that day (lowest 49.86 Hz), so FCR-D barely used any energy. FCR-N drives almost all of the cycling.

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

- FCR-D dynamic response (ramp to 86 % within 7.5 s) and FCR-D-heavy days
- Hourly bid sizes and hours without a bid
- Revenue estimate from FCR-N capacity prices (Fingrid/Svenska kraftnät market data)
- Battery ageing / cycle cost per day
- Run a whole month in the browser and rank the days

## Sources

- ENTSO-E, *Technical Requirements for Frequency Containment Reserve Provision in the Nordic Synchronous Area*, v1.1, 28 March 2025 (section 3.5, Table 10)
- Energinet, *Prequalification of FCR-N and FCR-D* (NEM and AEM implementation)
- Fingrid open data, dataset 339: frequency, historical data (0.1 s)
