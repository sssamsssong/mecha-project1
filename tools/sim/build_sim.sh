#!/bin/sh
# Build AUTO_CONTROL_PROJ_SIM (Linux/macOS/Pi, gcc) from the unmodified AUTO_CONTROL_PROJ.c
cd "$(dirname "$0")/../.." && gcc -O2 -Wall -Itools/sim/stub -o AUTO_CONTROL_PROJ_SIM AUTO_CONTROL_PROJ.c tools/sim/sim_hw.c -lm
