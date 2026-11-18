/* Simulated hardware for AUTO_CONTROL_PROJ.c (PC only)
 * - Time: every micros() call advances 50 us and integrates the motor model
 * - Motor: speed' = (Vmax * duty_eff - speed) / tau, duty below a deadzone gives no torque
 * - Encoder: position -> count (216/rev), each count step toggles A or B in
 *   quadrature order and calls the registered ISR, like the real Hall sensors
 * Model parameters can be changed with environment variables:
 *   SIM_VMAX [rev/s at 100%] (6.0), SIM_TAU [s] (0.06), SIM_DEADZONE [%] (8)
 */
#include <stdlib.h>
#include <math.h>
#include "wiringPi.h"
#include "softPwm.h"
#include "unistd.h"

#define SIM_STEP_US 50
#define PIN_A 17        /* ENCODERA */
#define PIN_B 27        /* ENCODERB */
#define PIN_M1 19       /* MOTOR1 (+ direction) */
#define PIN_M2 26       /* MOTOR2 (- direction) */
#define COUNTS_PER_REV 216

static unsigned int simTimeUs = 0;
static double pos = 0, speed = 0;          /* [rev], [rev/s] */
static long simCount = 0;
static int level[64];
static int duty[64];
static void (*isr[64])(void);
static double vmax = 6.0, tau = 0.06, deadzone = 8.0;

static double envOr(const char *name, double def)
{
    const char *v = getenv(name);
    return v ? atof(v) : def;
}

static void setQuadrature(long count, int *a, int *b)
{
    /* Forward order for DECODER logic: (A,B) = 00 -> 10 -> 11 -> 01 -> 00 */
    static const int A[4] = {0, 1, 1, 0}, B[4] = {0, 0, 1, 1};
    int s = (int)(((count % 4) + 4) % 4);
    *a = A[s]; *b = B[s];
}

static void stepEncoder(int dir)
{
    int a0, b0, a1, b1;
    setQuadrature(simCount, &a0, &b0);
    simCount += dir;
    setQuadrature(simCount, &a1, &b1);
    level[PIN_A] = a1; level[PIN_B] = b1;
    if (a0 != a1 && isr[PIN_A]) isr[PIN_A]();
    if (b0 != b1 && isr[PIN_B]) isr[PIN_B]();
}

static void advance(unsigned int us)
{
    for (unsigned int k = 0; k < us / SIM_STEP_US; k++) {
        double d = duty[PIN_M1] - duty[PIN_M2];
        double mag = fabs(d) > deadzone ? (fabs(d) - deadzone) / (100.0 - deadzone) : 0.0;
        double target = (d > 0 ? 1 : -1) * mag * vmax;
        double h = SIM_STEP_US * 1e-6;
        speed += (target - speed) / tau * h;
        pos += speed * h;
        long want = (long)floor(pos * COUNTS_PER_REV);
        while (simCount < want) stepEncoder(+1);
        while (simCount > want) stepEncoder(-1);
        simTimeUs += SIM_STEP_US;
    }
}

int wiringPiSetupGpio(void)
{
    vmax = envOr("SIM_VMAX", vmax);
    tau = envOr("SIM_TAU", tau);
    deadzone = envOr("SIM_DEADZONE", deadzone);
    return 0;
}
void pinMode(int pin, int mode) { (void)pin; (void)mode; }
void pullUpDnControl(int pin, int pud) { (void)pin; (void)pud; }
int digitalRead(int pin) { return level[pin]; }
int wiringPiISR(int pin, int edge, void (*func)()) { (void)edge; isr[pin] = (void (*)(void))func; return 0; }
void delay(unsigned int ms) { advance(ms * 1000); }
unsigned int millis(void) { advance(SIM_STEP_US); return simTimeUs / 1000; }
unsigned int micros(void) { advance(SIM_STEP_US); return simTimeUs; }
int softPwmCreate(int pin, int initialValue, int pwmRange) { (void)pwmRange; duty[pin] = initialValue; return 0; }
void softPwmWrite(int pin, int value)
{
    if (value < 0) value = 0;
    if (value > 100) value = 100;
    duty[pin] = value;
}
int geteuid(void) { return 0; }
int fchown(int fd, int owner, int group) { (void)fd; (void)owner; (void)group; return 0; }
