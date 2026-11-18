# AUTO_TUNE_PROJ
# Auto tuner: try gains on the real motor and find the best ones
#   1. Run AUTO_CONTROL_PROJ (C program) with gains, as root (sudo)
#   2. Get the score of the CSV file with EVALUATOR.py (smaller is better)
#      and show the project score A_k of the run with PROJECT_SCORE (smaller is better)
#   3. Decide the next gains in tune() and repeat
#   4. Draw all runs in one HTML graph with PLOT_GRAPH_PROJ.py (legend: PID gains)
# Write your own tuning method only in tune() (like positionControl() in C).
# Keep AUTO_CONTROL_PROJ, EVALUATOR.py, PROJECT_SCORE, PLOT_GRAPH_PROJ.py and this file in the same folder.
# Run: python3 AUTO_TUNE_PROJ.py

import os
import subprocess                   # Run a terminal command from Python
import time
from pathlib import Path
import EVALUATOR as ev              # Evaluation program (EVALUATOR.py)
import PROJECT_SCORE as ps          # Project score program (PROJECT_SCORE module)

os.chdir(Path(__file__).parent)     # Work in this file's folder (AUTO_CONTROL_PROJ, CSV files)

if not Path("AUTO_CONTROL_PROJ").exists():     # Program not built yet
    print("Error: AUTO_CONTROL_PROJ not found. Build it first:")
    print("  gcc -o AUTO_CONTROL_PROJ AUTO_CONTROL_PROJ.c -lwiringPi")
    exit()

# ===== Settings for running the motor =====
ENC_PER_REV = 216   # Encoder counts per 1 rev

csv_files = []      # CSV files of all runs (for the graph)

def run_motor(reference, gains, max_time):
    """Run AUTO_CONTROL_PROJ once and return the CSV file name.
    reference: target position [rev], gains: [P, I, D], max_time: run time [s]"""
    command = ["sudo", "./AUTO_CONTROL_PROJ", str(reference), str(max_time), str(ENC_PER_REV)]
    for gain in gains:                      # Add 3 gains at the end (P, I, D)
        command.append(str(gain))
    print("Run:", " ".join(command))        # Same as typing it in the terminal

    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:              # AUTO_CONTROL_PROJ failed
        print(result.stdout)
        exit()

    time.sleep(1)                           # Wait until the motor stops
    return result.stdout.split()[-1]        # Last word: "20261101_204818_P10_I0_D0.csv"


def test(reference, gains, max_time):
    """Run the motor to reference with gains and return the score (smaller is better)."""
    csv_file = run_motor(reference, gains, max_time)
    csv_files.append(csv_file)              # Keep it for the graph
    score = ev.get_score(csv_file)
    a_k = ps.get_score(csv_file)            # Project score A_k of this run (only shown here)
    print(f"-> score = {score:.5f}, A_k = {a_k:.5f}\n")
    return score


# ===== Tuning method (write your own here) =====
#   Use : score = test(reference, gains, max_time)
#         reference: target position [rev] (can be different every run)
#         gains: [P, I, D] (always 3 gains, 0 for a gain you do not use)
#         max_time: run time [s] (<= 10, can be different every run; A_k needs 5 to 10)
#   Return: best gains and best score
#   Any method is OK. Below is only a simple example.

def tune():
    """Find the best gains using test(reference, gains, max_time)."""
    # Example: move P by step, turn back with a half step if worse
    reference = 10      # Target position [rev] (same for all runs here)
    max_time = 5        # Run time [s] (same for all runs here, can be changed for each test)
    p = 10              # First P gain
    step = 5            # First change of P gain
    best_score = test(reference, [p, 0, 0], max_time)

    for i in range(2):  # Number of tries
        new_score = test(reference, [p + step, 0, 0], max_time)

        if new_score < best_score:      # Better: move there and keep going
            p = p + step
            best_score = new_score
        else:                           # Worse: turn back with a smaller step
            step = -step / 2

    return [p, 0, 0], best_score


# ===== Run tuning and show the result =====
best_gains, best_score = tune()

print("===== Result =====")
print(f"Best gains  : {best_gains}")
print(f"Best score  : {best_score:.5f}")
print(f"Motor runs  : {len(csv_files)}")

# Graph of all runs: run PLOT_GRAPH_PROJ.py with the CSV files
html_name = time.strftime("TUNE_%Y%m%d_%H%M%S")     # Answer to "Enter the HTML file name"
subprocess.run(["python3", "PLOT_GRAPH_PROJ.py"] + csv_files, input=html_name, text=True)
