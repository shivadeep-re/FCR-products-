"""Build the self-contained simulator page from one Fingrid 0.1 s frequency CSV.

Usage:
    python scripts/build_site.py data/Taajuusdata2026-08-29.csv            # writes site/index.html
    python scripts/build_site.py <csv> --out site/index.html
"""
import argparse, base64, datetime as dt, json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_day(csv_path):
    """Read one day, drop dropouts/spikes, return 864,000 samples on a 0.1 s grid."""
    d = pd.read_csv(csv_path, parse_dates=["Time"]).dropna().set_index("Time")["Value"]
    d = d[~d.index.duplicated()]
    d = d[(d > 49.0) & (d < 51.0)]                       # 0 Hz dropouts and gross errors
    med = d.rolling(9, center=True, min_periods=1).median()
    d = d[(d - med).abs() < 0.05]                         # single-sample spikes
    day = d.index[0].normalize()
    grid = pd.date_range(day, day + pd.Timedelta("1D") - pd.Timedelta("100ms"), freq="100ms")
    f = d.reindex(grid).ffill().bfill().to_numpy()
    return day.date(), f


def revenue_data(rev_dir):
    """Scenario results, hourly FCR prices and area volumes for the Revenue tab."""
    rev_dir = pathlib.Path(rev_dir)
    sc = pd.read_csv(rev_dir / "fcr_scenarios_2026-08.csv")
    keep = ["mix_id", "mix", "storage_h", "energy_MWh", "c_fcrn_MW", "c_fcrd_up_MW", "c_fcrd_down_MW", "gross_EUR",
            "import_MWh", "export_MWh", "throughput_MWh", "soc_change_MWh", "hours"]
    pr = pd.read_csv(rev_dir / "fcr_prices_hourly_2026-08.csv")
    vol = pd.read_csv(rev_dir / "fcr_volumes_daily_2026-08.csv")
    vm = vol.groupby(["area", "product"])["contracted_MW"].mean()
    key = {"FCR-N": "n", "FCR-D up": "du", "FCR-D down": "dd"}
    return {
        "period": [pr["time"].iloc[0][:10], pr["time"].iloc[-1][:10]],
        "scenarios": sc[keep].to_dict(orient="records"),
        "prices": {"t0": pr["time"].iloc[0], "n": pr["fcrn_EUR_MW"].round(3).tolist(),
                   "du": pr["fcrd_up_EUR_MW"].round(3).tolist(), "dd": pr["fcrd_down_EUR_MW"].round(3).tolist()},
        "volumes": {a: {key[p]: round(float(vm[(a, p)]), 2) for p in key} for a in vol["area"].unique()},
    }


def build(csv_path, out_path, rev_dir=None):
    day, f = load_day(csv_path)
    q = np.round((f - 50.0) * 1e5)                        # 0.01 mHz steps fit in int16 for |df| < 0.327 Hz
    if np.abs(q).max() >= 32767:
        raise ValueError("Frequency deviation too large for int16 encoding")
    b64 = base64.b64encode(q.astype("<i2").tobytes()).decode()
    html = (ROOT / "src/template.html").read_text()
    html = (html.replace("/*UPLOT_CSS*/", (ROOT / "src/vendor/uPlot.min.css").read_text())
                .replace("__DATA__", b64)
                .replace("__DATE_LONG__", f"{day.day} {day:%B %Y}")
                .replace("__DATE_ISO__", day.isoformat()))
    rev_dir = pathlib.Path(rev_dir) if rev_dir else ROOT / "results/revenue_2026-08"
    rev_html = (ROOT / "src/revenue_tab.html").read_text()
    rev_js = (ROOT / "src/revenue_tab.js").read_text().replace("__REV_DATA__", json.dumps(revenue_data(rev_dir), separators=(",", ":")))
    html = html.replace("<!--REV_HTML-->", rev_html).replace("/*REV_JS*/", rev_js)
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"Wrote {out} ({len(html)/1e6:.2f} MB) for {day}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--out", default=str(ROOT / "site/index.html"))
    ap.add_argument("--revenue", default=None, help="folder with the revenue results (default results/revenue_2026-08)")
    a = ap.parse_args()
    build(a.csv, a.out, a.revenue)
