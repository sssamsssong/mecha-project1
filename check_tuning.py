"""Read tuning histories or test AST-extracted helpers; never run/import a tuner."""

import argparse
import ast
import csv
import math
from pathlib import Path


def load_helpers():
    source = Path(__file__).with_name('AUTO_TUNE_PROJ.py')
    tree = ast.parse(source.read_text())
    namespace = {'math': math, 'ENC_PER_REV': 216}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name.startswith('_tuning_')]
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), namespace)
    return namespace


def self_test():
    helpers = load_helpers()
    recover = helpers['_tuning_no_movement']
    candidate, axis, _, reason = recover([0, 1e5, 1e5], 10, 10, [32, 4, 4])
    assert candidate == [10, 250, 33.75] and axis is None
    assert all(text in reason for text in ('D lock', 'I one-step saturation', 'P short'))
    assert recover([0, 0, 0], 10, 10, [32, 4, 4])[0] == [10, 0, 0]
    assert recover([10, 0, 0], 10, 10, [32, 4, 4])[0] == [320, 0, 0]
    assert recover([10, 0, 5], -10, 10, [32, 4, 4])[0] == [320, 0, 5]
    scale = helpers['_tuning_scaled_gain']
    assert scale([0, 0, 0], 1, 4, 5, 10) == 1
    assert scale([100, 0, 0], 1, 4, 5, 10) == 10
    assert scale([100, 0, 0], 2, 4, 5, 10) == 5
    metrics = {'steady_state_error': 10, 'rise_time': None,
               'overshoot_percent': 0, 'oscillations': 0}
    assert helpers['_tuning_response_step'](metrics, 0, 10, 5, 0) == 32
    motion = helpers['_tuning_motion_state']
    assert motion([0, 0], False, False, 1, [0, 0, 0], 0) == (0, False, False)
    assert motion([0, 0], False, False, 1, [0, 0, 5], 0) == (1, False, False)
    assert motion([0, 0], False, True, 2, [100, 0, 0], 0) == (1, True, True)
    assert motion([0, 0], False, True, 3, [100, 0, 0], 1) == (2, True, False)
    assert motion([0.1, 0.1], False, True, 2, [100, 0, 0], 0) == (1, True, False)
    assert motion([0, 1], True, True, 3, [100, 0, 0], 1) == (0, True, False)
    assess = helpers['_tuning_assess_response']
    # An unmoving response cannot initialize, improve, average, or fail.
    for best_score, scores in ((float('inf'), []), (100, [100])):
        for score in (0, 200):
            result = assess([100, 0, 0], score, False, [100, 0, 0], best_score, scores, .03)
            assert result[:3] == ([100, 0, 0], best_score, scores)
            assert result[3:7] == (False, False, False, False)
    result = assess([100, 0, 0], 200, True, [100, 0, 0], 100, [100], .03)
    assert result[1:3] == (150, [100, 200]) and result[3:7] == (False, False, True, True)
    assert assess([200, 0, 0], 97, True, [100, 0, 0], 100, [100], .03)[3]
    assert assess([200, 0, 0], 103, True, [100, 0, 0], 100, [100], .03)[4]
    assert assess([200, 0, 0], 102, True, [100, 0, 0], 100, [100], .03)[5]
    near = helpers['_tuning_near_failed']
    assert near([90, 110, 0], [(100, 100, 0)])
    assert not near([100, 100, .001], [(100, 100, 0)])
    print('PASS: AST-extracted helpers only; no tuner import or motor calls.')


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def reference_for(row, history):
    name = row.get('csv')
    if not name:
        return None
    for filename in (Path(name), history.parent / name, history.parent.parent / name):
        try:
            with filename.open(newline='') as source:
                reader = csv.reader(source)
                for _ in range(3):
                    next(reader)
                return number(next(reader)[2])  # Only the CSV header and first sample.
        except (OSError, StopIteration, IndexError):
            continue
    return None


def check_history(history, log):
    warnings = []
    previous_failure = None
    last_elapsed = None
    print('run | elapsed | P | I | D | A_k | moved | e_brake | brake_ratio | reason (60 chars)')
    with history.open(newline='') as source:
        for row in csv.DictReader(source):
            reason = row.get('reason', '')
            columns = [row.get(name, '') for name in
                       ('run', 'elapsed_s', 'P', 'I', 'D', 'A_k', 'moved', 'e_brake', 'brake_ratio')]
            print(' | '.join(columns + [reason[:60]]))
            run = row.get('run', '?')
            p_next = number(row.get('next_P'))
            i_next = number(row.get('next_I'))
            if p_next is not None and p_next > 100 * 216:
                warnings.append(f'run {run}: P > 21600 candidate (including return-to-best)')
            r = reference_for(row, history)
            if i_next is not None:
                if r is None or r == 0:
                    warnings.append(f'run {run}: reference unavailable; I saturation check skipped')
                elif i_next > 100 / (abs(r) * .01):
                    warnings.append(f'run {run}: I > i_sat candidate (including return-to-best)')
            gains = tuple(number(row.get(axis)) for axis in 'PID')
            failure = 'rule4: score at least 3% worse' in reason
            if failure and gains == previous_failure:
                warnings.append(f'run {run}: consecutive failure at the same gains')
            previous_failure = gains if failure else None
            last_elapsed = number(row.get('elapsed_s'))
    if last_elapsed is not None and last_elapsed > 60:
        warnings.append('last elapsed > 60 seconds')
    if log is not None:
        with log.open(errors='replace') as source:
            if not any('Final gains:' in line for line in source):
                warnings.append('Final gains: missing from terminal log')
    else:
        print('Log not supplied: Final gains: check skipped.')
    for warning in warnings:
        print('WARNING:', warning)
    if not warnings:
        print('No warnings in the available data (not a hardware safety guarantee).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('history', nargs='?', type=Path)
    parser.add_argument('log', nargs='?', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        self_test()
    elif args.history is not None:
        check_history(args.history, args.log)
    else:
        parser.error('provide a tuning CSV or --self-test')
