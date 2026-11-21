/* Read encoder only: GPIO17/27, both edges. No motor output. */
#include <stdio.h>
#include <signal.h>
#include <wiringPi.h>

#define ENCODERA 17
#define ENCODERB 27
#define COUNTS_PER_REV 216

static volatile sig_atomic_t stopped = 0;
static int previousState;
static int count = 0;
static int eventsA = 0;
static int eventsB = 0;
static int invalid = 0;

static void stop_check(int sig)
{
    (void)sig;
    stopped = 1;
}

static void read_encoder(int channel)
{
    /* Same count direction as AUTO_CONTROL_PROJ, four edges per cycle. */
    static const int step[16] = {
         0, -1,  1,  0,
         1,  0,  0, -1,
        -1,  0,  0,  1,
         0,  1, -1,  0
    };
    int state;
    piLock(0);
    state = digitalRead(ENCODERA) * 2 + digitalRead(ENCODERB);
    if (channel == 0) eventsA++;
    else eventsB++;
    if ((previousState ^ state) == 3) invalid++;
    count += step[previousState * 4 + state];
    previousState = state;
    piUnlock(0);
}

static void encoder_a(void) { read_encoder(0); }
static void encoder_b(void) { read_encoder(1); }

int main(void)
{
    int current = 0, a = 0, b = 0, bad = 0;
    if (wiringPiSetupGpio() < 0) return 1;
    pinMode(ENCODERA, INPUT);
    pinMode(ENCODERB, INPUT);
    pullUpDnControl(ENCODERA, PUD_OFF);
    pullUpDnControl(ENCODERB, PUD_OFF);
    previousState = digitalRead(ENCODERA) * 2 + digitalRead(ENCODERB);
    if (wiringPiISR(ENCODERA, INT_EDGE_BOTH, encoder_a) < 0 ||
        wiringPiISR(ENCODERB, INT_EDGE_BOTH, encoder_b) < 0) {
        fprintf(stderr, "엔코더 인터럽트 등록 실패\n");
        return 1;
    }
    signal(SIGINT, stop_check);
    signal(SIGTERM, stop_check);
    puts("모터 출력은 사용하지 않습니다. 다른 제어 프로그램은 종료하세요.");
    puts("축을 멈춘 상태에서 시작하세요. 출력축을 한 방향으로 천천히 정확히 1바퀴 돌린 뒤 Ctrl+C.");
    puts("감속기 축을 억지로 돌리지 마세요. A/B 외부 풀업과 엔코더 전원이 필요합니다.");
    while (!stopped) {
        piLock(0);
        current = count;
        a = eventsA;
        b = eventsB;
        bad = invalid;
        piUnlock(0);
        printf("\rCount=%d  Position(count/216)=%.3f rev  A=%d B=%d Invalid=%d   ",
               current, (float)current / COUNTS_PER_REV, a, b, bad);
        fflush(stdout);
        delay(200);
    }
    piLock(0);
    current = count;
    a = eventsA;
    b = eventsB;
    bad = invalid;
    piUnlock(0);
    printf("\n순카운트: %d (절댓값 %d)\n", current, current < 0 ? -current : current);
    printf("기존 216 기준 위치: %.3f rev\n", (float)current / COUNTS_PER_REV);
    printf("A/B 인터럽트: %d / %d, 두 비트 동시변화: %d\n", a, b, bad);
    puts("정확히 1바퀴 돌렸다면 순카운트 절댓값이 출력축 1바퀴당 계수입니다.");
    puts("동시변화는 정상 순서를 읽지 못했다는 뜻이며, 단락 여부를 확정하지는 않습니다.");
    return 0;
}
