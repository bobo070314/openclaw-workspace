@echo off
REM OpenClaw Evolution Engine Launcher (V5.0 Iron Lobster)
REM Auto-started via Windows Startup folder — no admin needed.
REM Crashes are handled by the engine's own retry loop.

cd /d D:\bobo\openclaw-foreign\core
C:\Python313\python.exe -u evolution_engine.py >> D:\bobo\openclaw-foreign\.deploy\logs\evolution_stdout.log 2>&1
