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
import csv                          # Tuning history
import math                         # Validate gains and responses
import sys                          # Optional initial gains
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
    reference = 10.0
    max_time = 5
    started = time.monotonic()
    if len(sys.argv) == 1:
        gains = [10.0, 0.0, 0.0]  # Original example's initial gains
    elif len(sys.argv) == 4:
        try:
            gains = [float(value) for value in sys.argv[1:]]
        except ValueError:
            raise SystemExit('Usage: python3 AUTO_TUNE_PROJ.py [P I D]')
    else:
        raise SystemExit('Usage: python3 AUTO_TUNE_PROJ.py [P I D]')
    if any(not math.isfinite(value) or value < 0 or value > 1e6 for value in gains):
        raise SystemExit('Gains must be finite and in the safety range 0 to 1000000.')

    # Starting position is zero: 100 / |error| makes the initial P output 100%.
    if gains[0] == 0:
        gains[0] = 100.0 / abs(reference)
    best_gains = gains[:]
    best_score = float('inf')
    previous_score = None
    previous_gains = None
    previous_axis = None
    previous_factor = None
    step = 2.0
    still_count = 0
    reserve = 4.0  # Allowance for evaluation, printing and graph generation
    run_allowance = max_time + 1.0

    Path('results').mkdir(exist_ok=True)
    history_path = Path('results') / ('tuning_' + time.strftime('%Y%m%d_%H%M%S') + '_' + str(os.getpid()) + '.csv')
    print('Tuning history:', history_path, flush=True)
    with history_path.open('x', newline='') as history:
        writer = csv.writer(history)
        writer.writerow(['run', 'P', 'I', 'D', 'score', 'A_k', 'rise_time',
                         'overshoot_percent', 'settling_time', 'steady_state_error',
                         'oscillations', 'moved', 'csv', 'next_P', 'next_I', 'next_D', 'reason'])
        while time.monotonic() - started + run_allowance + reserve <= 60.0:
            run_started = time.monotonic()
            score = test(reference, gains, max_time)
            run_allowance = max(run_allowance, time.monotonic() - run_started)
            filename = csv_files[-1]
            try:
                t, position, target = ev.read_csv(filename)
                metrics = ev.response_metrics(t, position, target)
                a_k = ps.evaluate(t, position, target)
                if not math.isfinite(score) or not math.isfinite(a_k) or len(t) < 2:
                    raise ValueError('invalid score or response')
                if any(not math.isfinite(float(value)) for values in (t, position, target) for value in values):
                    raise ValueError('non-finite response')
                if abs(float(t[-1]) - max_time) > 0.03:
                    raise ValueError('incomplete response')
                if max(abs(float(value)) for value in position) > 2.0 * abs(reference):
                    raise ValueError('dangerous position excursion')
            except (OSError, ValueError, IndexError) as exc:
                print('Tuning stopped:', exc, flush=True)
                writer.writerow([len(csv_files), *gains, score, '', '', '', '', '', '', '', filename, '', '', '', str(exc)])
                history.flush()
                raise SystemExit('Unsafe or invalid response; tuning stopped.')

            if score < best_score:
                best_score = score
                best_gains = gains[:]

            still_count = still_count + 1 if not metrics['moved'] else 0
            next_gains = gains[:]
            stop = False
            if still_count >= 2:
                reason = 'no movement twice; stop for safety'
                stop = True
            elif not metrics['moved']:
                # Use the observed error for 100% P output and grow much faster than 2x.
                error = abs(reference - float(position[-1]))
                next_gains[0] = max(100.0 / max(error, 0.001), gains[0] * 8.0)
                reason = 'no movement: boost P with 100/|error| and eightfold growth'
                previous_axis = None
            elif metrics['oscillations'] >= 4 or metrics['overshoot_percent'] >= 25:
                next_gains[0] *= 0.5
                next_gains[1] *= 0.5
                reason = 'large oscillation or overshoot: reduce P and I'
                previous_axis = None
            elif previous_score is not None and score > previous_score and gains != best_gains:
                next_gains = best_gains[:]
                step = 1.0 + (step - 1.0) / 2.0
                if previous_axis is not None and previous_gains == best_gains:
                    if best_gains[previous_axis] == 0:
                        next_gains[previous_axis] = gains[previous_axis] / step
                        previous_factor = 1.0 / step
                        reason = 'score worsened: return to best and reduce zero-origin step'
                    else:
                        factor = 1.0 / step if previous_factor > 1 else step
                        next_gains[previous_axis] *= factor
                        previous_factor = factor
                        reason = 'score worsened: return to best and try opposite direction with smaller step'
                else:
                    previous_axis = None
                    reason = 'score worsened: return to best measured gains'
            else:
                if previous_axis is not None and previous_score is not None and score < previous_score:
                    axis, factor = previous_axis, previous_factor
                    reason = 'score improved: continue previous direction'
                elif metrics['overshoot_percent'] > 2.0 or metrics['oscillations'] >= 2:
                    axis, factor = 2, step
                    reason = 'overshoot or oscillation: increase D'
                elif metrics['steady_state_error'] > 0.01 * abs(reference):
                    axis, factor = (1 if metrics['settling_time'] is not None else 0), step
                    reason = 'remaining error: increase I if settled, otherwise P'
                else:
                    axis, factor = 1, step
                    reason = 'small overshoot: explore I for remaining error'
                if next_gains[axis] == 0:
                    # Derive a first nonzero gain from current P and response duration.
                    next_gains[axis] = gains[0] / max_time if axis == 1 else gains[0] * max_time / 100.0
                    reason += '; seed from current P and response duration'
                else:
                    next_gains[axis] *= factor
                previous_axis, previous_factor = axis, factor

            next_gains = [min(1e6, max(0.0, value)) for value in next_gains]
            writer.writerow([len(csv_files), *gains, score, a_k, metrics['rise_time'],
                             metrics['overshoot_percent'], metrics['settling_time'],
                             metrics['steady_state_error'], metrics['oscillations'], metrics['moved'],
                             filename, *next_gains, reason])
            history.flush()
            print('Next:', next_gains, '-', reason, flush=True)
            if stop:
                raise SystemExit('No movement twice; tuning stopped for safety.')
            previous_score = score
            previous_gains = gains[:]
            gains = next_gains

    if not math.isfinite(best_score):
        raise SystemExit('No valid motor response; tuning stopped.')
    print('Final gains:', best_gains, flush=True)
    return best_gains, best_score


# ===== Run tuning and show the result =====
best_gains, best_score = tune()

print("===== Result =====")
print(f"Best gains  : {best_gains}")
print(f"Best score  : {best_score:.5f}")
print(f"Motor runs  : {len(csv_files)}")

# Graph of all runs: run PLOT_GRAPH_PROJ.py with the CSV files
html_name = time.strftime("TUNE_%Y%m%d_%H%M%S")     # Answer to "Enter the HTML file name"
subprocess.run(["python3", "PLOT_GRAPH_PROJ.py"] + csv_files, input=html_name, text=True)
