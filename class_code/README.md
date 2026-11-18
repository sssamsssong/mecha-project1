# 수업 실습 코드 (Week 2~9, 참고용)

출처: <https://github.com/GrindPear/Mecha2026> (메카트로닉스 2026 수업 리포, 커밋 `d8e22eb` 기준, 수정 없이 복사)
프로젝트 코드의 바탕이 된 실습 코드로, 참고용으로만 둔다. 프로젝트에서 실행하는 코드는 리포 루트에 있다.

| 폴더 | 날짜 | 수업 (실습 PDF) | 파일 |
|---|---|---|---|
| `Week_2` | 09/09~16 | C 언어 기초 (실습 1~3) | `foo.c` Hello World · `ArrayTest.c` 문자열/배열 · `FloatError.c` 부동소수점 비교 오차 · `SwitchCase.c` fall-through |
| `Week_4` | 09/28 | LED 구동 (실습 5) | `DigitalRead.c` · `LED_Blink.c` · `LED_Blink_handler.c` SIGINT 처리 · `Manu_PWM.c` · `HW_PWM.c` · `SW_PWM.c` softPwm · `Bright_arg.c` 실행 인자 · `tasks.json` VS Code 빌드 설정 |
| `Week_7` | 10/19 | 모터 제어 1 (실습 6) | `SWITCH_INTERRUPT.c` · `ENCODER_EXAMPLE.c` · `DECODER_EXAMPLE.c` x4 디코딩 · `MOTOR_PWM.c` · `SAMPLING_TIME_1.c` delay · `SAMPLING_TIME_2.c` millis 고정 주기 |
| `Week_9` | 11/02 | 모터 제어 2 (실습 7) | `P-CONTROL.c` · `DATA_LOGGING.c` CSV · `PLOT_GRAPH.py` · `AUTO_CONTROL.c` 실행 인자 제어기 · `EVALUATOR.py` · `AUTO_TUNE.py` |

수업 리포에 없는 것:
- 실습 3의 헤더 파일 예제(`main.c` + `funcA.c`)는 슬라이드에만 있다.
- Week_10·11(opencode 설정)은 팀 키를 쓰는 설정이라 이 리포에 넣지 않았다.

프로젝트 파일과 이름이 같은 파일이 있다(`EVALUATOR.py` 등). 이 폴더의 파일은 import하지 않는다.
