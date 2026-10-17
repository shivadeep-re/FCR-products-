"""Simulate a battery on FCR-N for every day in a folder of Fingrid 0.1 s CSVs (no energy management).

Usage:
    python scripts/analyse_month.py data/2026-08 results/fcrn_daily_2026-08.csv --power 1 --energy 2
"""
import argparse, glob, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from build_site import load_day


def simulate(f, power_mw, energy_mwh, eta_rt=0.90, soc0=0.5):
    dt = 0.1 / 3600
    eta = eta_rt ** 0.5
    df = f - 50.0
    p = -power_mw * np.clip(df / 0.1, -1, 1)              # + = discharge
    dis, chg = p[p > 0].sum() * dt, -p[p < 0].sum() * dt
    flows = np.where(p < 0, -p * eta, -p / eta) * dt
    e, empty, soc = energy_mwh * soc0, 0, np.empty_like(p)
    for i, x in enumerate(flows):                        # physical SOC, clipped 0..100 %
        e += x
        if e <= 0:
            e, empty = 0.0, empty + 1
        elif e > energy_mwh:
            e = energy_mwh
        soc[i] = e
    return dict(mean_abs_dev_mHz=np.abs(df).mean() * 1000,
                pct_outside_20mHz=np.mean(np.abs(df) > 0.02) * 100,
                pct_outside_band=np.mean(np.abs(df) > 0.1) * 100,
                fmin=f.min(), fmax=f.max(),
                discharge_MWh=dis, charge_MWh=chg, throughput_MWh=dis + chg, net_MWh=dis - chg,
                efc=(dis + chg) / (2 * energy_mwh),
                soc_min=soc.min() / energy_mwh * 100, soc_end=soc[-1] / energy_mwh * 100,
                hrs_empty=empty * 0.1 / 3600)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("out")
    ap.add_argument("--power", type=float, default=1.0); ap.add_argument("--energy", type=float, default=2.0)
    a = ap.parse_args()
    rows = []
    for path in sorted(glob.glob(os.path.join(a.folder, "*.csv"))):
        day, f = load_day(path)
        rows.append(dict(date=day, **simulate(f, a.power, a.energy)))
        print(day, f"{rows[-1]['throughput_MWh']:.2f} MWh")
    pd.DataFrame(rows).round(3).to_csv(a.out, index=False)
    print("Worst day by throughput:", max(rows, key=lambda r: r["throughput_MWh"])["date"])
