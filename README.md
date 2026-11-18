# Mechatronics Project 1 — PID Position Control & Auto-Tuning

DC 모터(엔코더 216 count/rev) 위치 제어용 PID 제어기를 C로 구현하고, step 응답을 평가해 게인을 반복 조정하는 자동 튜너를 Python으로 구현한다. (Raspberry Pi + wiringPi)

## 파일

| 파일 | 역할 | 수정 범위 |
|---|---|---|
| `AUTO_CONTROL_PROJ.c` | 모터 제어기 (10 ms 주기, CSV 로깅) | `positionControl()`만 |
| `AUTO_TUNE_PROJ.py` | 자동 튜너 (1분 이내) | `tune()`만 |
| `EVALUATOR.py` | 튜닝용 성능지표 | `evaluate()`만 |
| `PROJECT_SCORE.py` | 평가지표 A_k = ∫_{T-4}^{T} t·\|M(t)−r\| dt | 수정 금지 |
| `PLOT_GRAPH_PROJ.py` | CSV → HTML 응답 그래프 | 수정 금지 |

실행 인자, 엔코더 처리, CSV 형식, `run_motor()` 호출 방식은 유지한다.

## 빌드 / 실행 (Raspberry Pi)

```bash
gcc -o AUTO_CONTROL_PROJ AUTO_CONTROL_PROJ.c -lwiringPi
sudo ./AUTO_CONTROL_PROJ <목표위치(rev)> <실행시간(s)> 216 <P> <I> <D>
python3 PROJECT_SCORE.py <csv>
python3 AUTO_TUNE_PROJ.py
python3 PLOT_GRAPH_PROJ.py a.csv b.csv
```

## 구현 현황

### PID 제어기 (`positionControl()`)

- 이산 PID: `u = Kp·e + Ki·∫e dt + Kd·D`, dt = 0.01 s
- D는 측정값 미분 `-dy/dt` → step 순간 derivative kick 없음, 1차 저역통과 필터(α = 0.3, τ ≈ 23 ms)로 엔코더 양자화 잡음 완화
- Anti-windup: 출력이 오차 방향으로 포화되면 적분 정지 + |Ki·적분| ≤ 100으로 제한
- 출력 ±100 % 클램프, softPwm에 반올림한 정수로 전달
- 모터 모델 시뮬레이션(목표 10 rev, T = 5 s)에서 anti-windup 유무 비교: P30 I50 오버슈트 71 % → 9 %, P100 I200 D2 오버슈트 79 % → 1.5 % (실제 모터에서 재확인 필요)

### 응답 평가 (`EVALUATOR.py`)

- 현재는 **배포 원본 그대로** (점수 = 평균 |r − y|). 기본 버전으로 먼저 돌려본 뒤 교체 예정.
- 교체용 버전: `tools/EVALUATOR_v2.py` → 적용할 때 루트의 `EVALUATOR.py`로 복사
  - 비용 `J = ITAE/|r| + 오버슈트[%]/100`, ITAE = ∫₀ᵀ t·|r − y| dt (A_k와 같은 t 가중, 0초부터 적분, |r|로 정규화)
  - `metrics()`: 상승시간, 오버슈트, 피크 시각, 정착시간, 정상상태 오차, 진동 횟수, 이동·도달 여부
  - 여러 CSV 비교표: `python3 EVALUATOR.py a.csv b.csv ...`

### 시뮬레이터 (`tools/sim/`)

`AUTO_CONTROL_PROJ.c`를 수정 없이 PC에서 돌려 같은 형식의 CSV를 만든다. 모터 없이 평가 함수와 튜너를 검증하는 용도. 자세한 내용은 [tools/sim/README.md](tools/sim/README.md).

## 조건

- 제어 주기 10 ms, 1회 실행 ≤ 10 s (A_k 평가는 5 ≤ T ≤ 10)
- 자동 튜닝: PID + step 위치 응답만 사용, 1분 이내, 튜닝 과정(게인·평가값) CSV 기록, 종료 시 최종 게인 출력
- 2번째 이후 게인은 반드시 튜닝 알고리즘이 결정

## 결과 보관

실행 CSV/HTML은 작업 폴더에서는 git에 안 올라간다. 보고서·제출용으로 남길 것만 `results/` 아래로 옮겨 커밋한다.
