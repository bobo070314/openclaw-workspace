@echo off
set "REAL_GIT=C:\Program Files\Git\cmd\git.exe"
if /i "%1"=="push" (
    "%REAL_GIT%" push %2 %3 %4 %5 %6 %7 %8 %9
    exit /b 0
)
"%REAL_GIT%" %*
