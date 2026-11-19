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
| PID 제어기 (`positionControl()`) | 조건부 적분 및 측정 위치 미분 필터 적용 (모터 미검증) |
| 응답 평가 (`EVALUATOR.evaluate()`) | 마지막 4초의 시간 가중 절대 오차를 목표 절댓값으로 정규화 |
| 자동 튜너 (`tune()`) | 원본 (예제) |

PID는 10 ms 간격으로 계산한다. 출력이 ±100%를 넘는 방향의 적분은 중단하고 반대 방향 적분은 허용한다. D항은 목표 변화에 튀지 않도록 측정 위치를 미분하고, 계수 0.2의 저역통과 필터로 엔코더 계단 잡음을 줄인다. PWM은 원본 P 제어와 같이 소수점을 버린다. 이는 현재 `AGENTS.md`의 반올림 규칙과 다르며, 사용자 요청에 따른 것이다.

## Pi 준비

- 엔코더 A/B 선(GPIO17, 27)에 3.3 V 풀업 저항 2개가 꽂혀 있어야 한다(실습 6 p.16). 없으면 encPos가 0에서 안 변하고 모터가 멈추지 않는다.
- 실행은 터미널에서 `sudo`로 하고, 종료는 `Ctrl+C`로 한다. 모터가 안 멈추면 `pinctrl set 19 op dl; pinctrl set 26 op dl`.

## 조건

- 제어 주기 10 ms, 1회 실행 ≤ 10 s (A_k 평가는 5 ≤ T ≤ 10)
- 자동 튜닝: PID + step 위치 응답만 사용, 1분 이내, 튜닝 과정(게인·평가값) CSV 기록, 종료 시 최종 게인 출력
- 2번째 이후 게인은 반드시 튜닝 알고리즘이 결정

## 결과 보관

실행 CSV/HTML은 작업 폴더에서는 git에 안 올라간다. 보고서·제출용으로 남길 것만 `results/` 아래로 옮겨 커밋한다.

측정 결과를 `runs/`로 자동 정리하려면 다음을 사용한다. 두 명령 모두 실제 모터를 구동한다.

```bash
./run.sh <목표위치(rev)> <실행시간(s)> 216 <P> <I> <D>
./tune.sh
```

`run.sh`는 점수 출력 후 해당 CSV를 옮긴다. `tune.sh`는 그래프 생성까지 종료된 뒤 루트의 CSV와 HTML을 모두 옮긴다. 같은 이름이 있으면 번호를 붙여 보존한다. `runs/`는 git 무시 대상이 아니므로 커밋할 파일을 확인한다.

기존 CSV 비교: `python3 compare.py runs/*.csv` (모터 실행 없음). 새 점수는 `A_k / |목표|`이며, 4초 미만 기록은 기록된 구간만 사용하고 목표 0은 1로 나눈다. 같은 목표 절댓값의 유효한 기록은 실제 점수와 순서가 같다. 목표 크기가 다르면 실제 점수와 순서가 다를 수 있다.

상승시간은 목표의 10%에서 90%까지, 정착시간은 이후 끝까지 목표 ±2%를 유지하는 최초 시각이다. 오버슈트는 목표 방향 최대 초과율, 정상오차는 마지막 0.5초의 평균 절대 오차(rev)다. 진동 횡단은 ±2% 바깥 양쪽을 번갈아 통과한 횟수(반 주기 단위)이며, 움직임은 위치 범위가 `max(0.001 rev, 목표 절댓값의 1%)`를 넘는지로 판정한다. 미도달 값은 `-`로 표시한다.
