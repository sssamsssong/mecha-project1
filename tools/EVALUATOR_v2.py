# EVALUATOR
# Score of a CSV file from AUTO_CONTROL_PROJ (smaller is better) and step-response metrics
#   score J = ITAE / |r| + overshoot [%] / 100
#     ITAE = integral of t * |r - y(t)| dt over the whole run (same t-weighting as A_k,
#            but from t = 0 so the rising part also counts)
#     / |r|: makes runs with different targets comparable
#   metrics(): rise time, overshoot, settling time, steady-state error, oscillation count
#              (used by the auto tuner to decide the next gains, and for the report tables)
# Run: python3 EVALUATOR.py a.csv [b.csv ...]   -> score and metrics of each file

import sys
import numpy as np

COUNTS_PER_REV = 216
SETTLE_BAND_RATIO = 0.02            # Settling band: 2 % of |r| ...
SETTLE_BAND_MIN = 3 / COUNTS_PER_REV  # ... but at least 3 encoder counts [rev]
SS_WINDOW = 0.5                     # Steady-state error: mean of the last 0.5 s [s]
OVERSHOOT_WEIGHT = 1.0              # J penalty per 100 % overshoot


def read_csv(csv_file):
    """Read a CSV file and return time, position, target."""
    data = np.loadtxt(csv_file, delimiter=",", skiprows=3)     # skiprows=3: gain rows (2) and header row
    t = data[:, 0]              # Column 0: time (s)
    position = data[:, 1]       # Column 1: position (rev)
    target = data[:, 2]         # Column 2: target (rev)
    return t, position, target


def read_gains(csv_file):
    """Return [P, I, D] written in row 2 of the CSV file."""
    return list(np.loadtxt(csv_file, delimiter=",", skiprows=1, max_rows=1))


def integrate(t, f):
    """Trapezoid rule (works on old and new numpy)."""
    return float(np.sum((f[1:] + f[:-1]) / 2 * np.diff(t)))


def metrics(t, position, target):
    """Step-response metrics of one run (dict). Times in s, errors in rev, overshoot in %."""
    r = float(target[0])
    scale = abs(r) if r != 0 else 1.0
    e = r - position                            # Signed error
    ae = np.abs(e)
    p = position / r if r != 0 else np.zeros_like(position)   # Progress (1 = at target), works for r < 0
    band = max(SETTLE_BAND_RATIO * abs(r), SETTLE_BAND_MIN)

    def first_time(mask):
        idx = np.flatnonzero(mask)
        return float(t[idx[0]]) if idx.size else float("nan")

    t10, t90 = first_time(p >= 0.1), first_time(p >= 0.9)
    peak = int(np.argmax(p))
    overshoot = max(0.0, float(p[peak]) - 1.0) * 100

    outside = np.flatnonzero(ae > band)         # Settling: last time outside the band
    if outside.size == 0:
        settling = 0.0
    elif outside[-1] == len(t) - 1:
        settling = float("nan")                 # Still outside at the end
    else:
        settling = float(t[outside[-1] + 1])

    last = t >= t[-1] - SS_WINDOW
    ess = float(np.mean(ae[last]))
    ess_signed = float(np.mean(e[last]))        # + : stopped short, - : stopped beyond

    # Oscillation: sign changes of e outside the band (hysteresis, ignores encoder jitter)
    crossings, state = 0, 0
    for x in e:
        s = 1 if x > band else (-1 if x < -band else 0)
        if s != 0:
            if state != 0 and s != state:
                crossings += 1
            state = s

    return {
        "target": r,
        "run_time": float(t[-1]),
        "moved": bool(np.max(np.abs(position)) >= 2 / COUNTS_PER_REV),
        "reached": bool(np.any(p >= 0.9)),
        "rise_time": t90 - t10,
        "peak_time": float(t[peak]),
        "overshoot": overshoot,
        "settling_time": settling,
        "ess": ess,
        "ess_signed": ess_signed,
        "final_error": float(e[-1]),
        "crossings": crossings,
        "itae": integrate(t, t * ae) / scale,
    }


def evaluate(t, position, target):
    """Score of one run (smaller is better): J = ITAE/|r| + overshoot penalty."""
    m = metrics(t, position, target)
    return m["itae"] + OVERSHOOT_WEIGHT * m["overshoot"] / 100


def get_score(csv_file):
    """Read a CSV file and return its score (used by AUTO_TUNE_PROJ.py)."""
    t, position, target = read_csv(csv_file)
    return evaluate(t, position, target)


def get_metrics(csv_file):
    """Read a CSV file and return its metrics dict (used by the tuner and report tools)."""
    t, position, target = read_csv(csv_file)
    return metrics(t, position, target)


# Only when this file is run directly (not when imported by AUTO_TUNE_PROJ.py)
if __name__ == "__main__":
    import PROJECT_SCORE as ps
    print(f"{'file':<34} {'P':>6} {'I':>6} {'D':>5} {'r':>7} {'T':>5} {'J':>7} {'A_k':>8} "
          f"{'OS%':>6} {'tr':>5} {'ts':>5} {'ess':>6} {'osc':>3}")
    for f in sys.argv[1:]:
        g, m, score = read_gains(f), get_metrics(f), get_score(f)
        a_k = ps.get_score(f)
        print(f"{f[-34:]:<34} {g[0]:>6g} {g[1]:>6g} {g[2]:>5g} {m['target']:>7g} {m['run_time']:>5.2f} "
              f"{score:>7.4f} {a_k:>8.4f} {m['overshoot']:>6.2f} {m['rise_time']:>5.2f} "
              f"{m['settling_time']:>5.2f} {m['ess']:>6.4f} {m['crossings']:>3d}")
