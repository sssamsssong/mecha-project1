@echo off
rem Build AUTO_CONTROL_PROJ_SIM.exe (Windows, Visual Studio 2022) from the unmodified AUTO_CONTROL_PROJ.c
setlocal
cd /d "%~dp0..\.."
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1
if not exist build\sim mkdir build\sim
cl /nologo /W2 /D_CRT_SECURE_NO_WARNINGS /Itools\sim\stub /Fobuild\sim\ /Fe:AUTO_CONTROL_PROJ_SIM.exe AUTO_CONTROL_PROJ.c tools\sim\sim_hw.c
