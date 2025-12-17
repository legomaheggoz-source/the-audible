@echo off
TITLE The Audible - Weekly Deployment Protocol
COLOR 0A

ECHO ---------------------------------------------------
ECHO    🏈 THE AUDIBLE: WEEKLY UPDATE SEQUENCE 🏈
ECHO ---------------------------------------------------
ECHO.
ECHO  PRE-FLIGHT CHECK:
ECHO  1. Have you updated 'config.py' to the new week?
ECHO  2. Is your internet connection active?
PAUSE
ECHO.

:: ACTIVATE VIRTUAL ENV
call venv\Scripts\activate

:: STEP 1: FETCH DATA
ECHO  [1/4] 📡 Fetching Latest Data (03_fetch_history.py)...
python 03_fetch_history.py
IF %ERRORLEVEL% NEQ 0 (
    COLOR 0C
    ECHO.
    ECHO  ❌ CRITICAL ERROR: Data Fetch Failed. 
    ECHO  The process has been stopped. Fix the error above and try again.
    PAUSE
    EXIT /B
)
ECHO  ✅ Data Fetch Complete.
ECHO.

:: STEP 2: RUN PROJECTIONS
ECHO  [2/4] 🧠 Running Alpha Logic Projections...
python 05_make_projections.py
IF %ERRORLEVEL% NEQ 0 (
    COLOR 0C
    ECHO.
    ECHO  ❌ CRITICAL ERROR: Projections Failed.
    ECHO  The process has been stopped.
    PAUSE
    EXIT /B
)
ECHO  ✅ Projections Updated in Database.
ECHO.

:: STEP 3: RUN AUDIT
ECHO  [3/4] 📊 Verifying Database Integrity...
python 90_measure_accuracy.py
ECHO  ✅ Database Check Complete.
ECHO.

:: STEP 4: PUSH TO GITHUB (legomaheggoz-source/the-audible)
ECHO  [4/4] ☁️ Deploying to GitHub...
git add .
set /p commit_msg="Enter Commit Message (e.g., Week 16 Update): "
git commit -m "%commit_msg%"

:: This pushes to the specific repo you linked in Step 1
git push origin main
IF %ERRORLEVEL% NEQ 0 (
    COLOR 0C
    ECHO.
    ECHO  ❌ CRITICAL ERROR: Git Push Failed.
    ECHO  (Check your internet or GitHub credentials).
    PAUSE
    EXIT /B
)

ECHO.
ECHO ---------------------------------------------------
ECHO    🚀 SUCCESS! The Audible is live at:
ECHO    https://the-audible.streamlit.app
ECHO ---------------------------------------------------
PAUSE