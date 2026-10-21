"""Grid of product mix x starting SOC x storage hours x energy management for one month.

Usage:
    python scripts/mix_grid.py data/2026-08 results/mix_2026-08
"""
import argparse, itertools, os, sys, time
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from mix_analysis import load_month, run_mix, summarise

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("outdir")
    ap.add_argument("--power", type=float, default=1.0)
    ap.add_argument("--hours", default="1,1.5,2,3")
    ap.add_argument("--splits", default="100,80,60,50,40,20,0")
    ap.add_argument("--soc0", default="30,40,50,60,70")
    ap.add_argument("--cache", default="data/.cache")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    days, fr = load_month(a.folder, a.cache)
    print(f"Loaded {len(days)} days ({days[0]} to {days[-1]})", flush=True)
    rows, t0 = [], time.time()
    grid = list(itertools.product([float(h) for h in a.hours.split(",")], [int(s) for s in a.splits.split(",")],
                                  [float(s) for s in a.soc0.split(",")], (True, False)))
    for j, (h, s, s0, em) in enumerate(grid):
        cap = a.power * h
        caps, df = run_mix(fr, days, a.power, cap, s / 100, em=em, S0=s0, chained=True)
        rows.append(dict(storage_h=h, energy_MWh=cap, split_fcrn_pct=s, start_soc_pct=s0, energy_management=em, chained=True, **summarise(caps, df, cap)))
        if j % 20 == 0:
            print(f"{j+1}/{len(grid)}  {time.time()-t0:.0f} s", flush=True)
    # comparison: every day restarts at 50 % (2 h battery)
    for s in [int(v) for v in a.splits.split(",")]:
        for em in (True, False):
            caps, df = run_mix(fr, days, a.power, 2 * a.power, s / 100, em=em, S0=50.0, chained=False)
            rows.append(dict(storage_h=2.0, energy_MWh=2 * a.power, split_fcrn_pct=s, start_soc_pct=50.0, energy_management=em, chained=False, **summarise(caps, df, 2 * a.power)))
    out = os.path.join(a.outdir, "grid.csv")
    pd.DataFrame(rows).round(3).to_csv(out, index=False)
    print(f"Wrote {out}: {len(rows)} rows in {time.time()-t0:.0f} s")
