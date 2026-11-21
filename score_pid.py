#!/usr/bin/env python3
"""List project scores for matching PID gains in runs/."""

import argparse
import csv
import sys
from pathlib import Path

import PROJECT_SCORE as score


def main():
    parser = argparse.ArgumentParser(description="runs/에서 같은 PID의 점수를 나열합니다.")
    parser.add_argument("P", type=float)
    parser.add_argument("I", type=float)
    parser.add_argument("D", type=float)
    args = parser.parse_args()
    pid = (args.P, args.I, args.D)
    runs = Path(__file__).resolve().parent / "runs"
    if not runs.is_dir():
        print(f"폴더가 없습니다: {runs}", file=sys.stderr)
        return 1

    count = 0
    for path in sorted(runs.glob("*.csv")):
        try:
            with path.open(newline="") as f:
                rows = csv.reader(f)
                header = next(rows)
                if [item.strip() for item in header] != ["P gain", "I gain", "D gain"]:
                    continue
                gains = tuple(map(float, next(rows)))
            if gains != pid:
                continue
            t, position, target = score.read_csv(path)
            value = score.evaluate(t, position, target)
            print(f"{path.name} | 목표 {target[0]:g} | 시간 {t[-1]:g}s | A_k {value:.5f}")
            count += 1
        except (OSError, ValueError, IndexError, StopIteration) as exc:
            print(f"{path.name}: 읽기 실패 ({exc})", file=sys.stderr)
    if not count:
        print("일치하는 결과가 없습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
