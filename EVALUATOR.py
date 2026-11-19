# EVALUATOR
# Very simple score of a CSV file from AUTO_CONTROL (smaller is better)
#   score = average of |target - position| over the whole run [rev]
# Change only evaluate() to make your own score (like positionControl() in C).
# Run: python3 EVALUATOR.py a.csv

import sys
import numpy as np


def read_csv(csv_file):
    """Read a CSV file and return time, position, target."""
    data = np.loadtxt(csv_file, delimiter=",", skiprows=3)     # skiprows=3: gain rows (2) and header row
    t = data[:, 0]              # Column 0: time (s)
    position = data[:, 1]       # Column 1: position (rev)
    target = data[:, 2]         # Column 2: target (rev)
    return t, position, target


def evaluate(t, position, target):
    """Score of one run (smaller is better)."""
    r = float(target[0])
    scale = abs(r) if r != 0 else 1.0
    start = max(float(t[0]), float(t[-1]) - 4.0)
    error = np.abs(position - r)
    inside = t > start
    tw = np.concatenate(([start], t[inside]))
    ew = np.concatenate(([np.interp(start, t, error)], error[inside]))
    weighted = tw * ew
    return float(np.sum((weighted[1:] + weighted[:-1]) / 2 * np.diff(tw)) / scale)


def response_metrics(t, position, target):
    """Return step-response diagnostics; unavailable times are None."""
    r = float(target[0])
    scale = abs(r) if r != 0 else 1.0
    moved = bool(np.ptp(position) > max(0.001, 0.01 * scale))
    steady_error = float(np.mean(np.abs(position[t >= t[-1] - 0.5] - r)))
    metrics = {
        "rise_time": None,
        "overshoot_percent": None,
        "settling_time": None,
        "steady_state_error": steady_error,
        "oscillations": 0,
        "moved": moved,
    }
    if r == 0:
        return metrics

    progress = position / r
    t10 = np.flatnonzero(progress >= 0.1)
    if len(t10):
        t90 = np.flatnonzero((progress >= 0.9) & (t >= t[t10[0]]))
        if len(t90):
            metrics["rise_time"] = float(t[t90[0]] - t[t10[0]])
    metrics["overshoot_percent"] = float(max(0.0, (np.max(progress) - 1.0) * 100.0))

    outside = np.flatnonzero(np.abs(progress - 1.0) > 0.02)
    if not len(outside):
        metrics["settling_time"] = float(t[0])
    elif outside[-1] + 1 < len(t):
        metrics["settling_time"] = float(t[outside[-1] + 1])

    # Count full crossings of the ±2% band, ignoring noise inside it.
    side = 0
    for value in progress:
        new_side = 1 if value > 1.02 else -1 if value < 0.98 else 0
        if new_side:
            if side and new_side != side:
                metrics["oscillations"] += 1
            side = new_side
    return metrics


def get_score(csv_file):
    """Read a CSV file and return its score (used by AUTO_TUNE.py)."""
    t, position, target = read_csv(csv_file)
    return evaluate(t, position, target)


# Only when this file is run directly (not when imported by AUTO_TUNE.py)
if __name__ == "__main__":
    score = get_score(sys.argv[1])
    print(f"Score: {score:.5f}")
