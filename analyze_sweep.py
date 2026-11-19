#!/usr/bin/env python3
"""Summarize recorded manual sweeps and existing unclassified CSVs."""

import csv
import glob
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import EVALUATOR as ev
import PROJECT_SCORE as ps

ROOT = Path(__file__).resolve().parent
MANIFESTS = (ROOT / 'runs/sweep_manifest.tsv', ROOT / 'runs/sweep_manifest_v2.tsv')
SIMILARITY = 0.1  # Upper end of the observed A_k variation.
FIELDS = ('score', 'normalized', 'overshoot', 'settling', 'error', 'oscillations')


def summary(values):
    values = [value for value in values if value is not None and math.isfinite(value)]
    if not values:
        return '-', None
    mean = statistics.mean(values)
    spread = f'{statistics.stdev(values):.3f}' if len(values) > 1 else '-'
    return f'{mean:.3f}±{spread}({len(values)})', mean


def load_manifest():
    result = {}
    for manifest in MANIFESTS:
        if not manifest.exists():
            continue
        with manifest.open(newline='', encoding='utf-8') as stream:
            for row in csv.DictReader(stream, delimiter='\t'):
                if row['file'] != '-':
                    result[(ROOT / row['file']).resolve()] = row
    return result


def load_runs(files):
    manifest = load_manifest()
    groups = defaultdict(list)
    for name in files:
        path = Path(name).resolve()
        row = manifest.get(path)
        if row and row['status'] != 'ok':
            print(f'제외: {name} ({row["status"]})', file=sys.stderr)
            continue
        try:
            with path.open(encoding='utf-8', newline='') as stream:
                reader = csv.reader(stream)
                next(reader)
                gains = tuple(float(value.strip()) for value in next(reader))
            if len(gains) != 3 or not all(math.isfinite(x) for x in gains):
                raise ValueError('게인 형식 오류')
            t, position, target = ev.read_csv(str(path))
            if not all(math.isfinite(float(x)) for array in (t, position, target) for x in array):
                raise ValueError('유한하지 않은 데이터')
            reference = float(target[0])
            if reference == 0 or not (4.98 <= float(t[-1]) <= 10.02):
                raise ValueError('채점 불가능한 목표 또는 시간')
            if row and row.get('target'):
                requested = float(row['target'])
                duration = float(row['duration'])
                if abs(reference - requested) > 0.001 or abs(float(t[-1]) - duration) > 0.03:
                    raise ValueError('목록과 기록의 목표 또는 시간 불일치')
            elif row:
                duration = 5.0
                if abs(reference - 10) > 0.001 or abs(float(t[-1]) - duration) > 0.03:
                    raise ValueError('기존 목록은 목표 10, 시간 5만 허용')
            else:
                duration = round(float(t[-1]), 1)
            score = ps.evaluate(t, position, target)
            metrics = ev.response_metrics(t, position, target)
            stage = row['stage'] if row else '미분류'
            groups[(stage, gains, reference, duration)].append({
                'score': score,
                'normalized': score / abs(reference),
                'overshoot': metrics['overshoot_percent'],
                'settling': metrics['settling_time'],
                'error': metrics['steady_state_error'],
                'oscillations': metrics['oscillations'],
            })
        except (OSError, ValueError, IndexError, StopIteration) as exc:
            print(f'제외: {name} ({exc})', file=sys.stderr)
    return groups


def aggregate(groups):
    rows = []
    for (stage, gains, target, duration), runs in sorted(groups.items()):
        formatted, means = {}, {}
        for field in FIELDS:
            formatted[field], means[field] = summary([run[field] for run in runs])
        rows.append({'stage': stage, 'gains': gains, 'target': target, 'duration': duration, 'n': len(runs),
                     'formatted': formatted, 'means': means})
    return rows


def show_trends(rows):
    for stage in sorted({row['stage'] for row in rows}):
        for axis, label in enumerate(('P', 'I', 'D')):
            fixed = defaultdict(list)
            for row in rows:
                if row['stage'] == stage:
                    key = (row['target'], row['duration']) + tuple(value for index, value in enumerate(row['gains']) if index != axis)
                    fixed[key].append(row)
            for key, items in sorted(fixed.items()):
                if len(items) < 2:
                    continue
                others = [x for x in ('P', 'I', 'D') if x != label]
                print(f'단계 {stage}, 목표={key[0]:g}, 시간={key[1]:g}: {others[0]}={key[2]:g}, {others[1]}={key[3]:g} 고정; {label} 증가')
                for item in sorted(items, key=lambda x: x['gains'][axis]):
                    means = item['means']
                    value = lambda x: '-' if x is None else f'{x:.3f}'
                    print(f'  {label}={item["gains"][axis]:g}: A_k={value(means["score"])} A_k/|r|={value(means["normalized"])} '
                          f'오버슈트={value(means["overshoot"])}% '
                          f'정착={value(means["settling"])}s 정상오차={value(means["error"])}rev')


def ranked(candidates):
    candidates = sorted(candidates, key=lambda row: row['means']['score'])
    ordered = []
    while candidates:
        best = candidates[0]['means']['score']
        similar = [row for row in candidates if row['means']['score'] - best < SIMILARITY]
        candidates = candidates[len(similar):]
        similar.sort(key=lambda row: (row['means']['overshoot'], row['means']['oscillations'], row['means']['score']))
        ordered.extend((row, len(similar) > 1) for row in similar)
    return ordered


def recommend(rows):
    candidates = [row for row in rows if row['stage'] == '1' and row['gains'][1] == 0 and row['target'] == 10 and row['duration'] == 5]
    if not candidates:
        print('\n1단계 추천: 기록된 정상 완료 데이터 없음 (기존 데이터는 미분류).')
        return
    ordered = ranked(candidates)
    print('\n2단계 후보 (A_k 차이 < 0.1이면 비슷함; 오버슈트, 진동 횡단 순):')
    for row, similar in ordered[:2]:
        p, _, d = row['gains']
        print(f'P={p:g} D={d:g}: A_k={row["means"]["score"]:.3f}, '
              f'오버슈트={row["means"]["overshoot"]:.3f}%, '
              f'진동 횡단={row["means"]["oscillations"]:.2f}' + (' (비슷함)' if similar else ''))


def main():
    files = sys.argv[1:] or sorted(glob.glob(str(ROOT / 'runs/*.csv')))
    rows = aggregate(load_runs(files))
    if not rows:
        print('분석 가능한 CSV가 없습니다.', file=sys.stderr)
        return 1
    print('평균±표본표준편차(유효 횟수); 횟수 1의 표준편차는 -')
    print('단계 | P | I | D | 목표 | 시간 | 횟수 | A_k | A_k/|목표| | 오버슈트(%) | 정착시간(s) | 정상오차(rev) | 진동 횡단')
    for row in rows:
        p, i, d = row['gains']
        values = ' | '.join(row['formatted'][key] for key in FIELDS)
        print(f'{row["stage"]} | {p:g} | {i:g} | {d:g} | {row["target"]:g} | {row["duration"]:g} | {row["n"]} | {values}')
    print('\n경향 (평균; 정착시간은 정착한 실행만 포함):')
    show_trends(rows)
    recommend(rows)
    return 0


if __name__ == '__main__':
    sys.exit(main())
