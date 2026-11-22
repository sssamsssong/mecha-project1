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

def _tuning_scaled_gain(gains, axis, factor, max_time, error):
    """Scale a gain; seed zero only after a measured response."""
    value = gains[axis]
    if value == 0:
        # If P is zero, derive its scale from the measured error, not a target gain.
        p_scale = gains[0] if gains[0] > 0 else 100.0 / max(error, 0.001)
        if axis == 0:
            value = p_scale
        elif axis == 1:
            return gains[0] / (2.0 * max_time)  # rule1: no response multiplier
        else:
            return p_scale * max_time / 100.0  # rule1: existing D seed, unscaled
    return value * factor


def _tuning_response_step(metrics, axis, reference, max_time, peak_progress):
    """Choose a relative step from response severity: P up to 32, I/D up to 4."""
    error_ratio = metrics['steady_state_error'] / abs(reference)
    if axis == 0:
        rise_time = metrics['rise_time']
        if rise_time is None:
            # No 90% arrival: use the observed shortfall, not a fabricated rise time.
            rise_ratio = max(0.0, (0.9 - peak_progress) / 0.9)
        else:
            rise_ratio = rise_time / max_time
        severity = max(error_ratio, rise_ratio)
    elif axis == 1:
        severity = error_ratio / 0.01
    else:
        severity = max(metrics['overshoot_percent'] / 25.0,
                       metrics['oscillations'] / 4.0)
    severity = min(1.0, max(0.0, severity))
    multiplier = 31.0 if axis == 0 else 3.0
    return max(1.25, 1.0 + multiplier * severity)


def _tuning_near_failed(gains, failed_gains):
    """rule3: all axes must be within 10% of one failed combination."""
    return any(all((value == 0 if failed == 0 else
                    value != 0 and 0.9 * failed <= value <= 1.1 * failed)
                   for value, failed in zip(gains, trial))
               for trial in failed_gains)


def _tuning_unfailed_candidate(base_gains, blocked_axes, steps, failed_gains,
                              metrics, max_time, error, allow_blocked=False):
    """Explore one axis from a measured baseline, avoiding failed regions."""
    preferred = 2 if metrics['overshoot_percent'] > 2.0 or metrics['oscillations'] >= 2 else (
        1 if metrics['settling_time'] is not None else 0)
    axes = [preferred] + [axis for axis in range(3) if axis != preferred]
    axes = ([axis for axis in axes if axis not in blocked_axes]
            + ([axis for axis in axes if axis in blocked_axes] if allow_blocked else []))
    skipped = False
    for axis in axes:
        for direction in (1, -1):
            factor = steps[axis] if direction > 0 else 1.0 / steps[axis]
            candidate = base_gains[:]
            candidate[axis] = _tuning_scaled_gain(base_gains, axis, factor, max_time, error)
            candidate = [min(1e6, max(0.0, value)) for value in candidate]
            if candidate != base_gains:
                if _tuning_near_failed(candidate, failed_gains):
                    skipped = True
                else:
                    return candidate, axis, factor, skipped
    return None, None, None, skipped


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
    if any(not math.isfinite(value) or value < 0 for value in gains):
        raise SystemExit('Gains must be finite and non-negative.')

    # The evaluator's initial gains, including all zeros, are measured unchanged.
    best_gains = gains[:]
    best_score = float('inf')
    best_scores = []
    failed_gains = []  # Only this tuning session, never past/manual experiments
    previous_score = None
    previous_overshoot = None
    previous_gains = None
    previous_axis = None
    previous_factor = None
    previous_retry = False
    previous_reduce = False
    improvement_threshold = 0.03
    still_count = 0
    reserve = 4.0  # Allowance for evaluation, printing and graph generation
    run_allowance = max_time + 1.0

    Path('results').mkdir(exist_ok=True)
    history_path = Path('results') / ('tuning_' + time.strftime('%Y%m%d_%H%M%S') + '_' + str(os.getpid()) + '.csv')
    print('Tuning history:', history_path, flush=True)
    with history_path.open('x', newline='') as history:
        writer = csv.writer(history)
        writer.writerow(['run', 'elapsed_s', 'P', 'I', 'D', 'score', 'A_k', 'rise_time',
                         'overshoot_percent', 'settling_time', 'steady_state_error',
                         'oscillations', 'moved', 'csv', 'next_P', 'next_I', 'next_D', 'reason'])
        while time.monotonic() - started + run_allowance + reserve <= 60.0:
            run_started = time.monotonic()
            score = test(reference, gains, max_time)
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
                writer.writerow([len(csv_files), time.monotonic() - started, *gains,
                                 score, '', '', '', '', '', '', '', filename, '', '', '', str(exc)])
                history.flush()
                raise SystemExit('Unsafe or invalid response; tuning stopped.')

            evaluated = time.monotonic()
            elapsed = evaluated - started
            run_allowance = max(run_allowance, evaluated - run_started)
            # Compare against the best before updating it. At a zero best score,
            # an equal score stays equivalent and any positive score is a failure.
            first_trial = not math.isfinite(best_score)
            repeat_best = not first_trial and gains == best_gains
            best_gap = (None if first_trial else
                        (score - best_score) / best_score if best_score > 0 else
                        (0.0 if score == 0 else float('inf')))
            improved = (first_trial or
                        (not repeat_best and score < best_score
                         and score <= best_score * (1.0 - improvement_threshold)))
            failed_trial = (not first_trial and not repeat_best and score > best_score
                            and score >= best_score * (1.0 + improvement_threshold))
            equivalent = not improved and not failed_trial
            if improved:
                best_score = score
                best_gains = gains[:]
                best_scores = [score]
            elif repeat_best:
                best_scores.append(score)
                best_score = sum(best_scores) / len(best_scores)
            if failed_trial:
                failed_gains.append(tuple(gains))
            improvement = ((previous_score - score) / max(abs(previous_score), 1e-12)
                           if previous_score is not None else None)
            # An intentionally unpowered first measurement is not a motor failure.
            unpowered_initial = previous_score is None and gains[0] == 0 and gains[1] == 0
            still_count = still_count + 1 if not metrics['moved'] and not unpowered_initial else 0
            error = abs(reference - float(position[-1]))
            peak_progress = max(float(value) / reference for value in position)
            steps = [_tuning_response_step(metrics, axis, reference, max_time, peak_progress)
                     for axis in range(3)]
            next_gains = gains[:]
            stop = False
            exhausted = False
            next_axis = None
            next_factor = None
            next_retry = False
            next_reduce = False
            returning_best = False
            seed_base = gains
            blocked_axes = set()
            skipped_failed = False
            changed_axes = ({axis for axis in range(3)
                             if previous_gains[axis] != gains[axis]}
                            if previous_gains is not None else set())
            if still_count >= 3:
                reason = 'no movement three times; stop for safety'
                stop = True
            elif not metrics['moved']:
                # Bootstrap zero from measured error; grow nonzero P by response severity.
                next_gains[0] = max(100.0 / max(error, 0.001), gains[0] * steps[0])
                reason = 'no movement: boost P from measured error and response severity'
                if gains[2] > 0:
                    # rule6: a large D can brake the motor before it moves.
                    next_gains[2] = gains[2] / steps[0]
                    reason += '; rule6: reduce D by the same factor'
                next_axis, next_factor = 0, steps[0]
            elif failed_trial and previous_retry:
                next_gains = best_gains[:]
                returning_best = True
                seed_base = best_gains
                reason = 'rule2: P plus D retry failed; return to best gains'
            elif (failed_trial and not previous_reduce and previous_gains is not None
                  and changed_axes == {2} and gains[2] > previous_gains[2]
                  and best_gains[2] > 0):
                # rule6: more damping made it worse, so the overshoot is not from too
                # little damping. Reduce I and D from the best gains instead.
                step = max(steps[0], steps[2])
                next_gains = best_gains[:]
                next_gains[1] = best_gains[1] / step
                next_gains[2] = best_gains[2] / step
                seed_base = best_gains
                next_axis, next_factor, next_reduce = 2, 1.0 / step, True
                reason = f'rule6: D increase failed; reduce I and D from best; factor=1/{step:.4f}'
            elif (failed_trial and previous_gains is not None
                  and gains[0] > previous_gains[0]):
                next_gains[2] = _tuning_scaled_gain(gains, 2, steps[2], max_time, error)
                next_axis, next_factor = 2, steps[2]
                next_retry = True
                reason = 'rule2: P increase failed; try D increase at the same P and I'
                if min(1e6, next_gains[2]) <= gains[2]:
                    next_gains = best_gains[:]
                    returning_best = True
                    seed_base = best_gains
                    next_axis, next_factor, next_retry = None, None, False
                    reason += '; D cannot increase within safety range: return to best'
            elif failed_trial:
                next_gains = best_gains[:]
                returning_best = True
                seed_base = best_gains
                reason = 'rule4: failed trial; return to best gains'
            elif equivalent:
                blocked_axes = changed_axes
                if previous_axis is not None:
                    blocked_axes = blocked_axes | {previous_axis}
                next_gains, next_axis, next_factor, skipped_failed = _tuning_unfailed_candidate(
                    gains, blocked_axes, steps, failed_gains, metrics, max_time, error)
                reason = 'rule4: equivalent to best; switch axis'
                if next_gains is None:
                    next_gains, next_axis, next_factor, skipped = _tuning_unfailed_candidate(
                        gains, blocked_axes, steps, failed_gains, metrics, max_time, error,
                        allow_blocked=True)
                    skipped_failed = skipped_failed or skipped
                    reason += '; all axes blocked: allow blocked axes'
                if next_gains is None:
                    next_gains = best_gains[:]
                    exhausted = True
                    reason += '; no unfailed alternative: finish'
            elif metrics['oscillations'] >= 4 or metrics['overshoot_percent'] >= 25:
                # Keep P: dividing P and I together leaves the I/P ratio unchanged.
                step = steps[2]
                next_gains[1] /= step
                next_gains[2] = _tuning_scaled_gain(gains, 2, step, max_time, error)
                reason = f'large oscillation or overshoot: reduce I, increase D at the same P; factor={step:.4f}'
            else:
                direction = 1
                if previous_reduce and improved:
                    # rule6: the reduction improved the score; continue with the same step.
                    step = max(steps[0], steps[2], 1.0 / previous_factor)
                    next_gains[1] = gains[1] / step
                    next_gains[2] = gains[2] / step
                    next_axis, next_factor, next_reduce = 2, 1.0 / step, True
                    reason = f'rule6: reduction improved; continue reducing; factor=1/{step:.4f}'
                    axis = None
                elif previous_overshoot is not None and metrics['overshoot_percent'] > previous_overshoot:
                    axis = 2
                    reason = 'overshoot increased from previous response: increase D'
                elif metrics['overshoot_percent'] > 2.0 or metrics['oscillations'] >= 2:
                    axis = 2
                    reason = 'overshoot or oscillation: increase D'
                elif previous_axis is not None and improved and not first_trial:
                    axis = previous_axis
                    direction = 1 if previous_factor > 1 else -1
                    reason = 'rule4: score improved at least 3% versus best; continue previous direction'
                elif metrics['steady_state_error'] > 0.01 * abs(reference):
                    axis = 1 if metrics['settling_time'] is not None else 0
                    reason = 'remaining error: increase I if settled, otherwise P'
                else:
                    axis = 1 if metrics['settling_time'] is not None else 0
                    reason = 'small overshoot: explore I for remaining error'
                    if axis == 0:
                        reason = 'not settled: explore P before increasing I'
                if axis is not None:
                    step = steps[axis]
                    factor = step if direction > 0 else 1.0 / step
                    next_gains[axis] = _tuning_scaled_gain(next_gains, axis, factor, max_time, error)
                    next_axis, next_factor = axis, factor
                    reason += f'; axis={"PID"[axis]}, trial_factor={factor:.4f}'

            if not returning_best:
                next_gains = [min(1e6, max(0.0, value)) for value in next_gains]
            if failed_trial:
                reason += '; rule4: score at least 3% worse than best'
            elif improved:
                reason += '; rule4: ' + ('first valid best' if first_trial else 'new best by at least 3%')
            elif repeat_best:
                reason += f'; rule5: best gains remeasured; mean score={best_score:.5f}'
            if not stop and not exhausted and _tuning_near_failed(next_gains, failed_gains):
                if next_retry:
                    reason += '; rule2: D retry blocked by rule3; return to best baseline'
                blocked = blocked_axes | ({next_axis} if next_axis is not None else set())
                candidate, axis, factor, skipped = _tuning_unfailed_candidate(
                    best_gains, blocked, steps, failed_gains, metrics, max_time, error,
                    allow_blocked=not equivalent)
                skipped_failed = skipped_failed or skipped
                if candidate is None:
                    next_gains = best_gains[:]
                    exhausted = True
                    reason += '; rule3: failed-near PID skipped; no unfailed alternative: finish'
                else:
                    next_gains = candidate
                    seed_base = best_gains
                    next_axis, next_factor = axis, factor
                    next_retry = False
                    reason += (f'; rule3: failed-near PID skipped; alternative from best:'
                               f' axis={"PID"[axis]}, trial_factor={factor:.4f}')
            if skipped_failed:
                reason += '; rule3: failed-near alternative skipped'
            if not stop and not exhausted:
                for axis in (1, 2):
                    if seed_base[axis] == 0 and next_gains[axis] > 0:
                        reason += f'; rule1: {"PID"[axis]} zero-origin seed without multiplier'
            previous_comparison = ('first' if improvement is None
                                   else f'{100.0 * improvement:.2f}%')
            gap_text = 'first' if best_gap is None else f'{100.0 * best_gap:.2f}%'
            reason += (f'; improvement_vs_previous={previous_comparison}'
                       f'; gap_vs_best={gap_text}')
            writer.writerow([len(csv_files), elapsed, *gains, score, a_k, metrics['rise_time'],
                             metrics['overshoot_percent'], metrics['settling_time'],
                             metrics['steady_state_error'], metrics['oscillations'], metrics['moved'],
                             filename, *next_gains, reason])
            history.flush()
            print('Next:', next_gains, '-', reason, flush=True)
            if stop:
                raise SystemExit('No movement three times; tuning stopped for safety.')
            if exhausted:
                break
            previous_score = score
            previous_overshoot = metrics['overshoot_percent']
            previous_gains = gains[:]
            previous_axis, previous_factor = next_axis, next_factor
            previous_retry = next_retry
            previous_reduce = next_reduce
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
