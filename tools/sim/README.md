# 모터 시뮬레이터 (PC 테스트용)

`AUTO_CONTROL_PROJ.c`를 **수정 없이** PC에서 빌드해 실행하는 도구. wiringPi 대신 `stub/` 헤더와 `sim_hw.c`를 링크한다.

- 시간: `micros()`를 부를 때마다 50 µs씩 진행하면서 모터 모델을 적분
- 모터: `speed' = (Vmax·duty_eff − speed) / τ`, 데드존 아래 duty는 토크 0
- 엔코더: 위치를 216 count/rev로 바꾸고, count가 바뀔 때마다 A/B를 quadrature 순서로 토글하면서 실제 ISR(`funcEncoderA/B`)을 호출
- 출력 CSV, 파일 이름, 터미널 출력이 실제 프로그램과 같아서 `EVALUATOR.py`, `PROJECT_SCORE.py`, `PLOT_GRAPH_PROJ.py`에 그대로 넣을 수 있다

## 빌드 / 실행

```powershell
tools\sim\build_sim.bat                                  # Windows (Visual Studio 2022)
.\AUTO_CONTROL_PROJ_SIM.exe 10 5 216 100 50 2
python EVALUATOR.py <생성된 csv>
```

```bash
sh tools/sim/build_sim.sh                                # Linux / Pi (gcc)
./AUTO_CONTROL_PROJ_SIM 10 5 216 100 50 2
```

## 모델 파라미터 (환경변수)

| 변수 | 기본값 | 의미 |
|---|---|---|
| `SIM_VMAX` | 6.0 | duty 100 %일 때 속도 [rev/s] (실습 7 그래프 기울기 기준) |
| `SIM_TAU` | 0.06 | 속도 응답 시정수 [s] |
| `SIM_DEADZONE` | 8 | 모터가 안 도는 duty [%] |

실제 모터와 수치는 다르다. 알고리즘이 맞게 동작하는지, 발산하거나 시간을 초과하지 않는지 확인하는 용도로만 쓰고, 게인 값은 반드시 실제 모터에서 정한다.
