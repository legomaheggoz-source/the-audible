@echo off
cd /d "C:\Users\Dell\Desktop\Gridiron_Project"

echo ========================================================
echo      🏈 THE AUDIBLE - WEEKLY STATS RECAP (TUESDAY) 🏈
echo ========================================================
echo.

:: --- STEP 0: ACTIVATE ENVIRONMENT ---
echo [0/5] 🔌 Activating Virtual Environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ ERROR: Could not activate .venv.
    pause
    exit /b 1
)

:: 1. UPDATE ROSTERS
echo.
echo [1/5] 📋 Updating Active Player Roster (02_fetch_players.py)...
python 02_fetch_players.py
if %errorlevel% neq 0 goto error

:: 2. DOWNLOAD GAME RESULTS
echo.
echo [2/5] 📚 Downloading Latest Game Results (03_fetch_history.py)...
python 03_fetch_history.py
if %errorlevel% neq 0 goto error

:: 3. BACKFILL & AUDIT (New Steps)
echo.
echo [3/5] 💾 Archiving History & Grading Accuracy (06 & 90)...
python 06_backfill_history.py
python 90_measure_accuracy.py
if %errorlevel% neq 0 goto error

:: 4. UPDATE ODDS
echo.
echo [4/5] 🎰 Fetching Latest Vegas Odds (04_update_features.py)...
python 04_update_features.py
if %errorlevel% neq 0 goto error

:: 5. GENERATE PROJECTIONS
echo.
echo [5/5] 🔮 Recalculating Week %CURRENT_WEEK% Projections (05_make_projections.py)...
python 05_make_projections.py
if %errorlevel% neq 0 goto error

:: --- CLOUD DEPLOYMENT (GIT) ---

echo.
echo ========================================================
echo       ☁️  SYNCING HISTORY TO STREAMLIT CLOUD...
echo ========================================================

echo.
echo 📦 Staging ALL Changes (DB + Code)...
git add .

echo 📝 Committing Changes...
git commit -m "Weekly Stats Update: %date% %time%"

echo 🚀 Pushing to GitHub...
git push origin main
if %errorlevel% neq 0 goto git_error

echo.
echo ========================================================
echo   ✅ SUCCESS: Weekly history updated!
echo ========================================================
pause
exit /b 0

:error
echo.
echo ❌ CRITICAL PYTHON ERROR: A script failed. No data was pushed.
pause
exit /b 1

:git_error
echo.
echo ❌ GIT ERROR: Could not push to GitHub.
pause
exit /b 1