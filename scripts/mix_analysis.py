"""Month-long analysis of FCR-N / FCR-D product mixes with Nordic NEM/AEM.

Same model as the website (src/template.html), compiled with numba so a whole
month at 0.1 s runs in seconds. SOC is carried from one day to the next.

Usage:
    python scripts/mix_analysis.py data/2026-08 results/mix_2026-08 --power 1 --energy 2
"""
import argparse, glob, json, os, sys
import numpy as np
import pandas as pd
from numba import njit

sys.path.insert(0, os.path.dirname(__file__))
from build_site import load_day

N_DAY = 864_000


def split_caps(P, CAP, share_n, use_n=True, use_du=True, use_dd=True):
    """Port of applySplit() in the page: most each product can bid from its power share, scaled to fit energy."""
    any_d = use_du or use_dd
    s = share_n
    if not use_n:
        s = 0.0
    if not any_d:
        s = 1.0
    cn = s * P / 1.34 if use_n else 0.0
    both = use_du and use_dd
    cd = (1 - s) * P / (1.2 if both else 1.0) if any_d else 0.0
    if any_d and not both:
        cd = min(cd, (P - 1.34 * cn) / 0.2)
    cdu, cdd = (cd if use_du else 0.0), (cd if use_dd else 0.0)
    need = (cn + cdu / 3) + (cn + cdd / 3)
    if need > CAP:
        k = CAP / need
        cn, cdu, cdd = cn * k, cdu * k, cdd * k
    fl = lambda v: np.floor(v * 100 + 1e-6) / 100
    return fl(cn), fl(cdu), fl(cdd)


@njit(cache=True)
def simulate(fr, P, CAP, S0, RT, CN, CDu, CDd, em, n_day):
    """Port of compute() in the page. Returns per-day statistics."""
    n = fr.size
    days = n // n_day
    DT = 0.1 / 3600.0
    ETA = np.sqrt(RT)
    resUp, resDn = CDu / 3.0, CDd / 3.0
    E = CAP * S0 / 100.0
    lowN = highN = aemN = aemDu = aemDd = nemDu = nemDd = False
    bN = np.zeros(300, np.int8); bDu = np.zeros(300, np.int8); bDd = np.zeros(300, np.int8)
    fBuf = np.full(300, 50.0)
    sN = sDu = sDd = 0; fSum = 50.0 * 300; k = 0
    cN = cDu = cDd = 0.0; fref = 50.0
    # per-day outputs
    soc_min = np.full(days, 101.0); soc_max = np.full(days, -1.0); soc_end = np.zeros(days)
    thr = np.zeros(days); eN = np.zeros(days); eD = np.zeros(days); eM = np.zeros(days)
    aem_s = np.zeros(days); empty_s = np.zeros(days); full_s = np.zeros(days); nem_s = np.zeros(days); fcrd_s = np.zeros(days)
    for i in range(days * n_day):
        d = i // n_day
        f = fr[i]
        if em:
            if CN > 0:
                up = (E - resUp) / CN * 60; dn = (CAP - E - resDn) / CN * 60
                if up < 30: lowN = True
                elif up > 57.5: lowN = False
                if dn < 30: highN = True
                elif dn > 57.5: highN = False
                if up <= 5 or dn <= 5: aemN = True
                elif up > 10 and dn > 10: aemN = False
            if CDu > 0:
                up = E / CDu * 60; nemDu = up < 20
                if up <= 5: aemDu = True
                elif up > 10: aemDu = False
            if CDd > 0:
                dn = (CAP - E) / CDd * 60; nemDd = dn < 20
                if dn <= 5: aemDd = True
                elif dn > 10: aemDd = False
            if i % 10 == 0:
                normal = f > 49.9 and f < 50.1
                aN = 0
                if normal and CN > 0:
                    aN = -1 if lowN else (1 if highN else 0)
                aDu = -1 if (normal and nemDu) else 0
                aDd = 1 if (normal and nemDd) else 0
                sN += aN - bN[k]; bN[k] = aN
                sDu += aDu - bDu[k]; bDu[k] = aDu
                sDd += aDd - bDd[k]; bDd[k] = aDd
                fSum += f - fBuf[k]; fBuf[k] = f; k = (k + 1) % 300
                cN = sN / 300.0; cDu = sDu / 300.0; cDd = sDd / 300.0; fref = fSum / 300.0
        sh = fref - 50.0
        vN = 0.0; vD = 0.0
        if CN > 0:
            r = ((fref if (em and aemN) else 50.0) - f) / 0.1
            vN = (1.0 if r > 1 else (-1.0 if r < -1 else r)) * CN
        if CDu > 0:
            fu = f - sh if (em and aemDu) else f
            r = (49.9 - fu) / 0.4
            vD += (1.0 if r > 1 else (0.0 if r < 0 else r)) * CDu
        if CDd > 0:
            fd = f - sh if (em and aemDd) else f
            r = (fd - 50.1) / 0.4
            vD -= (1.0 if r > 1 else (0.0 if r < 0 else r)) * CDd
        vM = (0.34 * CN * cN + 0.2 * CDu * cDu + 0.2 * CDd * cDd) if em else 0.0
        v = vN + vD + vM
        if v > P: v = P
        elif v < -P: v = -P
        inA = em and (aemN or aemDu or aemDd)
        if vM != 0: nem_s[d] += 0.1
        if inA: aem_s[d] += 0.1
        if vD != 0: fcrd_s[d] += 0.1
        eN[d] += abs(vN) * DT; eD[d] += abs(vD) * DT; eM[d] += abs(vM) * DT; thr[d] += abs(v) * DT
        E += (-v * ETA if v < 0 else -v / ETA) * DT
        if E <= 0:
            E = 0.0
            if v > 0: empty_s[d] += 0.1
        if E >= CAP:
            E = CAP
            if v < 0: full_s[d] += 0.1
        sc = E / CAP * 100
        if sc < soc_min[d]: soc_min[d] = sc
        if sc > soc_max[d]: soc_max[d] = sc
        soc_end[d] = sc
    return soc_min, soc_max, soc_end, thr, eN, eD, eM, aem_s, empty_s, full_s, nem_s, fcrd_s


def load_month(folder, cache_dir):
    os.makedirs(cache_dir, exist_ok=True)
    days, arrs = [], []
    for path in sorted(glob.glob(os.path.join(folder, "*.csv"))):
        c = os.path.join(cache_dir, os.path.basename(path) + ".npy")
        if os.path.exists(c):
            f = np.load(c); day = pd.Timestamp(os.path.basename(path)[-14:-4]).date()
        else:
            day, f = load_day(path); np.save(c, f.astype(np.float64))
        days.append(day); arrs.append(np.asarray(f, np.float64))
    return days, np.concatenate(arrs)


def run_mix(fr, days, P, CAP, share, use=(True, True, True), em=True, S0=50.0, RT=0.9, chained=True):
    cn, cdu, cdd = split_caps(P, CAP, share, *use)
    if chained:
        out = simulate(fr, P, CAP, S0, RT, cn, cdu, cdd, em, N_DAY)
    else:  # every day starts from S0
        parts = [simulate(fr[i * N_DAY:(i + 1) * N_DAY], P, CAP, S0, RT, cn, cdu, cdd, em, N_DAY) for i in range(len(days))]
        out = tuple(np.concatenate([p[j] for p in parts]) for j in range(12))
    names = ["soc_min", "soc_max", "soc_end", "throughput_MWh", "fcrn_MWh", "fcrd_MWh", "nem_MWh", "aem_s", "empty_s", "full_s", "nem_s", "fcrd_s"]
    df = pd.DataFrame(dict(zip(names, out)))
    df.insert(0, "date", days)
    return (cn, cdu, cdd), df


def summarise(caps, df, CAP):
    m = df["soc_min"].to_numpy()
    return dict(c_fcrn_MW=caps[0], c_fcrd_up_MW=caps[1], c_fcrd_down_MW=caps[2],
                soc_min_worst=m.min(), soc_min_p95=np.percentile(m, 5), soc_min_median=np.median(m),
                worst_day=str(df.loc[df["soc_min"].idxmin(), "date"]),
                days_below_10=int((m < 10).sum()), aem_h=df["aem_s"].sum() / 3600, empty_h=df["empty_s"].sum() / 3600,
                full_h=df["full_s"].sum() / 3600, nem_h=df["nem_s"].sum() / 3600, fcrd_active_min=df["fcrd_s"].sum() / 60,
                throughput_MWh=df["throughput_MWh"].sum(), cycles_per_day=df["throughput_MWh"].mean() / (2 * CAP),
                soc_end_month=df["soc_end"].iloc[-1])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("outdir")
    ap.add_argument("--power", type=float, default=1.0); ap.add_argument("--energy", type=float, default=2.0)
    ap.add_argument("--splits", default="100,80,60,50,40,20,0", help="FCR-N share of power in %%")
    ap.add_argument("--cache", default="data/.cache")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    days, fr = load_month(a.folder, a.cache)
    rows = []
    for s in [int(v) for v in a.splits.split(",")]:
        for em in (True, False):
            caps, df = run_mix(fr, days, a.power, a.energy, s / 100, em=em)
            df.round(4).to_csv(os.path.join(a.outdir, f"daily_split{s:03d}_{'em' if em else 'noem'}.csv"), index=False)
            rows.append(dict(split_fcrn_pct=s, energy_management=em, **summarise(caps, df, a.energy)))
            r = rows[-1]
            print(f"split {s:3d}% em={em!s:5}: P95 min SOC {r['soc_min_p95']:5.1f}%  worst {r['soc_min_worst']:5.1f}%  AEM {r['aem_h']:5.1f} h  empty {r['empty_h']:5.1f} h  thr {r['throughput_MWh']:6.1f} MWh")
    pd.DataFrame(rows).round(3).to_csv(os.path.join(a.outdir, "summary.csv"), index=False)
