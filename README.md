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

모든 코드는 **배포 원본 상태**에서 Pi의 AI(opencode)로 하나씩 구현한다.

| 항목 | 상태 |
|---|---|
| PID 제어기 (`positionControl()`) | 원본 (P 제어만) |
| 응답 평가 (`EVALUATOR.evaluate()`) | 원본 (평균 \|r − y\|) |
| 자동 튜너 (`tune()`) | 원본 (예제) |

## Pi 준비

- 엔코더 A/B 선(GPIO17, 27)에 3.3 V 풀업 저항 2개가 꽂혀 있어야 한다(실습 6 p.16). 없으면 encPos가 0에서 안 변하고 모터가 멈추지 않는다.
- 실행은 터미널에서 `sudo`로 하고, 종료는 `Ctrl+C`로 한다. 모터가 안 멈추면 `pinctrl set 19 op dl; pinctrl set 26 op dl`.

## 조건

- 제어 주기 10 ms, 1회 실행 ≤ 10 s (A_k 평가는 5 ≤ T ≤ 10)
- 자동 튜닝: PID + step 위치 응답만 사용, 1분 이내, 튜닝 과정(게인·평가값) CSV 기록, 종료 시 최종 게인 출력
- 2번째 이후 게인은 반드시 튜닝 알고리즘이 결정

## 결과 보관

실행 CSV/HTML은 작업 폴더에서는 git에 안 올라간다. 보고서·제출용으로 남길 것만 `results/` 아래로 옮겨 커밋한다.
