@echo off
set "REAL_GIT=C:\Program Files\Git\cmd\git.exe"
set "WRAPPER=%cd%\v1.1-self-evo-factory\scripts\git_safe_push.py"
if /i "%1"=="push" if exist "%WRAPPER%" (
    python "%WRAPPER%" %2 %3 %4 %5
    exit /b %ERRORLEVEL%
)
"%REAL_GIT%" %*
