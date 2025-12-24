@echo off
cd /d "C:\Users\Dell\Desktop\Gridiron_Project"

echo ========================================================
echo      🔒 THE AUDIBLE - SUNDAY LOCK (SNAPSHOT) 🔒
echo ========================================================
echo.

:: ACTIVATE
call .venv\Scripts\activate.bat

:: RUN SNAPSHOT
echo 📸 Taking snapshot of final projections...
python 08_snapshot_week.py
if %errorlevel% neq 0 goto error

echo.
echo ✅ SNAPSHOT SECURE. You are ready for kickoff.
pause
exit /b 0

:error
echo ❌ Snapshot failed.
pause