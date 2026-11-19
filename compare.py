#!/usr/bin/env python3
"""Compare existing CSV files without running the motor."""

import sys

import EVALUATOR as ev
import PROJECT_SCORE as ps


def display(value, digits=3):
    return "-" if value is None else f"{value:.{digits}f}"


def main(files):
    if not files:
        print("사용법: python3 compare.py a.csv b.csv ...", file=sys.stderr)
        return 2
    print("파일 | 목표 | 새 점수 | A_k | 상승(s) | 오버슈트(%) | 정착(s) | 정상오차(rev) | 진동 횡단 | 움직임")
    failed = False
    for file in files:
        try:
            t, position, target = ev.read_csv(file)
            score = ev.evaluate(t, position, target)
            actual = ps.evaluate(t, position, target)
            metrics = ev.response_metrics(t, position, target)
            print(f"{file} | {target[0]:g} | {score:.5f} | {actual:.5f} | "
                  f"{display(metrics['rise_time'])} | {display(metrics['overshoot_percent'])} | "
                  f"{display(metrics['settling_time'])} | {metrics['steady_state_error']:.3f} | "
                  f"{metrics['oscillations']} | {'예' if metrics['moved'] else '아니오'}")
        except (OSError, ValueError, IndexError) as exc:
            print(f"{file}: {exc}", file=sys.stderr)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
