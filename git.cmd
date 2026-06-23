@echo off
set "REAL_GIT=C:\Program Files\Git\cmd\git.exe"
if /i "%1"=="push" (
    python "D:\bobo\openclaw-foreign\workspace\scripts\git_safe_push.py" %2 %3 %4 %5 %6 %7 %8 %9
    exit /b %ERRORLEVEL%
)
"%REAL_GIT%" %*
exit /b %ERRORLEVEL%
