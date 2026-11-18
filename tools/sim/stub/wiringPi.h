/* Simulation stub of wiringPi (PC only, see tools/sim/README.md) */
#pragma once
#define TRUE 1
#define FALSE 0
#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INT_EDGE_FALLING 1
#define INT_EDGE_RISING 2
#define INT_EDGE_BOTH 3
#define PUD_OFF 0
int wiringPiSetupGpio(void);
void pinMode(int pin, int mode);
void pullUpDnControl(int pin, int pud);
int digitalRead(int pin);
int wiringPiISR(int pin, int edge, void (*func)());
void delay(unsigned int ms);
unsigned int millis(void);
unsigned int micros(void);
