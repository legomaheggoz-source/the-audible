@echo off
cd /d "C:\Users\Dell\Desktop\Gridiron_Project"

echo ========================================================
echo      🏈 THE AUDIBLE - DAILY INTELLIGENCE UPDATE 🏈
echo ========================================================
echo.

:: --- STEP 0: ACTIVATE ENVIRONMENT ---
echo [0/3] 🔌 Activating Virtual Environment...
call .venv\Scripts\activate.bat
if %errorlevel% neq 0 (
    echo ❌ ERROR: Could not activate .venv. Run "python -m venv .venv" first.
    pause
    exit /b 1
)

:: --- STEP 1: PYTHON PROCESSING ---

echo.
echo [1/3] 📋 Updating Active Player Roster (02_fetch_players.py)...
python 02_fetch_players.py
if %errorlevel% neq 0 goto error

echo.
echo [2/3] 🎰 Fetching Latest Vegas Odds & Schedule (04_update_features.py)...
python 04_update_features.py
if %errorlevel% neq 0 goto error

echo.
echo [3/3] 🔮 Recalculating Week %CURRENT_WEEK% Projections (05_make_projections.py)...
python 05_make_projections.py
if %errorlevel% neq 0 goto error

:: --- STEP 2: CLOUD DEPLOYMENT (GIT) ---

echo.
echo ========================================================
echo       ☁️  SYNCING TO STREAMLIT CLOUD...
echo ========================================================

echo.
echo 📦 Staging ALL Changes (DB + Code)...
git add .

echo 📝 Committing Changes...
git commit -m "Daily Data Update: %date% %time%"

echo 🚀 Pushing to GitHub...
git push origin main
if %errorlevel% neq 0 goto git_error

echo.
echo ========================================================
echo   ✅ SUCCESS: App updated! Check Streamlit in ~2 mins.
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
echo    - Check your internet connection.
echo    - Make sure you don't have unmerged changes.
pause
exit /b 1