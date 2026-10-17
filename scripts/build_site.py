"""Build the self-contained simulator page from one Fingrid 0.1 s frequency CSV.

Usage:
    python scripts/build_site.py data/Taajuusdata2026-08-29.csv            # writes site/index.html
    python scripts/build_site.py <csv> --out site/index.html
"""
import argparse, base64, datetime as dt, pathlib
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


def build(csv_path, out_path):
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
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"Wrote {out} ({len(html)/1e6:.2f} MB) for {day}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--out", default=str(ROOT / "site/index.html"))
    a = ap.parse_args()
    build(a.csv, a.out)
