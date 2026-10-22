"""Gross and net FCR revenue per product mix and storage size, for one month.

Inputs: a folder of Fingrid 0.1 s frequency CSVs and a Svenska kraftnät (Mimer)
FCR price export (semicolon-separated, decimal comma, hourly EUR/MW prices).

Usage:
    python scripts/revenue.py data/2026-08 data/FCR_2026-08.csv results/revenue_2026-08
"""
import argparse, json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from mix_analysis import load_month, split_caps, simulate, N_DAY

PRICE_COLS = {"N": "FCR-N Pris (EUR/MW)", "Du": "FCR-D upp Pris (EUR/MW)", "Dd": "FCR-D ned Pris (EUR/MW)"}
VOL_COLS = {"N": "{a} FCRN", "Du": "{a} FCRD upp", "Dd": "{a} FCRD ned"}

# name, FCR-N share of power, use FCR-N, FCR-D up, FCR-D down
MIXES = [
    ("FCR-N only", 1.0, True, False, False),
    ("80/20 N/D", 0.8, True, True, True),
    ("60/40 N/D", 0.6, True, True, True),
    ("50/50 N/D", 0.5, True, True, True),
    ("40/60 N/D", 0.4, True, True, True),
    ("20/80 N/D", 0.2, True, True, True),
    ("FCR-D up+down", 0.0, False, True, True),
    ("FCR-D up only", 0.0, False, True, False),
    ("FCR-D down only", 0.0, False, False, True),
    ("50/50 N/D-up", 0.5, True, True, False),
]


def load_prices(path):
    df = pd.read_csv(path, sep=";", decimal=",", encoding="utf-8-sig")
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df = df[df["Datum"].astype(str).str.match(r"^\d{4}-")].copy()   # drop the "Summa" row
    df["Datum"] = pd.to_datetime(df["Datum"])
    for c in df.columns[1:]:
        df[c] = pd.to_numeric(df[c])
    return df.set_index("Datum").sort_index()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("freq_folder"); ap.add_argument("prices"); ap.add_argument("outdir")
    ap.add_argument("--power", type=float, default=1.0)
    ap.add_argument("--hours", default="1,1.5,2,3")
    ap.add_argument("--soc0", type=float, default=50.0)
    ap.add_argument("--eff", type=float, default=0.90)
    ap.add_argument("--cache", default="data/.cache")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    days, fr = load_month(a.freq_folder, a.cache)
    pr = load_prices(a.prices)
    t0 = pd.Timestamp(days[0])
    sim_hours = pd.date_range(t0, periods=len(days) * 24, freq="h")
    common = sim_hours.intersection(pr.index)            # hours that have both frequency and prices
    hidx = sim_hours.get_indexer(common)
    p = {k: pr.loc[common, c].to_numpy() for k, c in PRICE_COLS.items()}
    rows, hourly = [], {}
    for hrs in [float(h) for h in a.hours.split(",")]:
        cap = a.power * hrs
        for name, share, un, udu, udd in MIXES:
            cn, cdu, cdd = split_caps(a.power, cap, share, un, udu, udd)
            out = simulate(fr, a.power, cap, a.soc0, a.eff, cn, cdu, cdd, True, N_DAY)
            imp, exp_, unav, soc = (x[hidx] for x in out[12:16])
            avail = 1 - np.clip(unav, 0, 1)
            gN, gDu, gDd = (float((c * p[k] * avail).sum()) for c, k in ((cn, "N"), (cdu, "Du"), (cdd, "Dd")))
            soc_start = a.soc0 if hidx[0] == 0 else out[15][hidx[0] - 1]
            key = f"{hrs:g}h|{name}"
            rows.append(dict(storage_h=hrs, energy_MWh=cap, mix=name, c_fcrn_MW=cn, c_fcrd_up_MW=cdu, c_fcrd_down_MW=cdd,
                             gross_fcrn_EUR=gN, gross_fcrd_up_EUR=gDu, gross_fcrd_down_EUR=gDd, gross_EUR=gN + gDu + gDd,
                             import_MWh=float(imp.sum()), export_MWh=float(exp_.sum()),
                             throughput_MWh=float(imp.sum() + exp_.sum()),
                             soc_change_MWh=float((soc[-1] - soc_start) / 100 * cap),
                             unavailable_h=float(unav.sum()), soc_min_pct=float(soc.min()), hours=len(common)))
            hourly[key] = dict(imp=np.round(imp, 5).tolist(), exp=np.round(exp_, 5).tolist())
            r = rows[-1]
            print(f"{hrs:>3g} h  {name:<16} C={cn:.2f}/{cdu:.2f}/{cdd:.2f}  gross €{r['gross_EUR']:>7,.0f}  thr {r['throughput_MWh']:5.1f} MWh  net import {r['import_MWh']-r['export_MWh']:5.2f} MWh  unavail {r['unavailable_h']:.2f} h", flush=True)
    res = pd.DataFrame(rows)
    res.round(4).to_csv(os.path.join(a.outdir, "scenarios.csv"), index=False)
    areas = ["SE1", "SE2", "SE3", "SE4", "DK2"]
    vol = pd.DataFrame({f"{ar}_{k}": pr.loc[common, VOL_COLS[k].format(a=ar)] for ar in areas for k in VOL_COLS})
    out = dict(period=[str(common[0]), str(common[-1])], hours=len(common),
               price_hourly={k: np.round(v, 4).tolist() for k, v in p.items()},
               time=[t.strftime("%Y-%m-%d %H:%M") for t in common],
               volumes_mean_MW={c: round(float(vol[c].mean()), 2) for c in vol.columns},
               volumes_daily_MW={c: np.round(vol[c].groupby(common.date).mean().to_numpy(), 2).tolist() for c in vol.columns},
               scenarios=res.round(4).to_dict(orient="records"), hourly_flows=hourly)
    with open(os.path.join(a.outdir, "revenue.json"), "w") as f:
        json.dump(out, f)
    print("hours with prices:", len(common), common[0], "to", common[-1])
