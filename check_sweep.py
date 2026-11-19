#!/usr/bin/env python3
"""Stop a manual sweep if a completed measurement is missing or abnormal."""
import csv
import sys

import numpy as np

import EVALUATOR as ev


def main():
    try:
        file, target, duration, p, i, d = sys.argv[1:]
        target, duration, p, i, d = map(float, (target, duration, p, i, d))
        with open(file, newline='') as stream:
            reader = csv.reader(stream)
            next(reader)
            gains = [float(x) for x in next(reader)]
        if len(gains) != 3 or not np.allclose(gains, [p, i, d], rtol=1e-5, atol=1e-6):
            raise ValueError('게인 불일치')
        t, position, reference = ev.read_csv(file)
        if len(t) < 2 or not all(np.all(np.isfinite(x)) for x in (t, position, reference)):
            raise ValueError('데이터 부족 또는 비정상 값')
        if not np.all(np.diff(t) > 0) or abs(float(t[-1]) - duration) > 0.03:
            raise ValueError('기록 시간 오류')
        if not np.allclose(reference, target, atol=0.001, rtol=1e-6):
            raise ValueError('목표 불일치')
        if np.ptp(position) < 0.001:
            raise ValueError('기록된 위치가 변하지 않음')
    except (OSError, ValueError, IndexError, StopIteration) as exc:
        print(f'이상 감지: {exc} — 스윕 중단', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
