# PROJECT_SCORE
# Project score A_k of a CSV file from AUTO_CONTROL_PROJ (smaller is better)
#   Run k: target r_k [rev], position M_k(t) [rev], run time T_k [s]
#     E_k(t) = |M_k(t) - r_k|
#     A_k    = integral of t * E_k(t) dt, from T_k - 4 to T_k   (last 4 seconds)
#   Rules: 5 <= T_k <= 10, r_k != 0   (if not, the score is nan)
# Same form as EVALUATOR.py: read_csv(), evaluate(), get_score()
# Run: python3 PROJECT_SCORE.py a.csv

import sys
import numpy as np

WINDOW = 4.0        # Evaluate the last 4 seconds of the run [s]
MIN_TIME = 5.0      # Shortest run time [s]
MAX_TIME = 10.0     # Longest run time [s]
TIME_TOL = 0.02     # Allowed error of the run time [s] (2 samples)


def read_csv(csv_file):
    """Read a CSV file and return time, position, target."""
    data = np.loadtxt(csv_file, delimiter=",", skiprows=3)     # skiprows=3: gain rows (2) and header row
    t = data[:, 0]              # Column 0: time (s)
    position = data[:, 1]       # Column 1: position (rev)
    target = data[:, 2]         # Column 2: target (rev)
    return t, position, target


def evaluate(t, position, target):
    """Project score A_k of one run (smaller is better)."""
    r = target[0]           # Target position r_k
    run_time = t[-1]        # Run time T_k (time of the last row)

    if r == 0:
        print("PROJECT_SCORE: not valid (target must not be 0)")
        return float("nan")
    if run_time < MIN_TIME - TIME_TOL or run_time > MAX_TIME + TIME_TOL:
        print(f"PROJECT_SCORE: not valid (run time is {run_time:g} s, must be {MIN_TIME:g} to {MAX_TIME:g} s)")
        return float("nan")

    start = run_time - WINDOW               # Integrate from T_k - 4 to T_k
    error = np.abs(position - r)            # E_k(t) at each time

    # Points of t * E_k(t) inside the window (first point: straight line between two rows)
    inside = t > start
    tw = np.concatenate(([start], t[inside]))
    fw = tw * np.concatenate(([np.interp(start, t, error)], error[inside]))

    # Integral (trapezoid rule)
    return float(np.sum((fw[1:] + fw[:-1]) / 2 * np.diff(tw)))


def get_score(csv_file):
    """Read a CSV file and return its project score A_k (used by AUTO_TUNE_PROJ.py)."""
    t, position, target = read_csv(csv_file)
    return evaluate(t, position, target)


# Only when this file is run directly (not when imported by AUTO_TUNE_PROJ.py)
if __name__ == "__main__":
    score = get_score(sys.argv[1])
    print(f"Score: {score:.5f}")
