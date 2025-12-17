@echo off
echo 🏈 STARTING GRIDIRON WEEKLY UPDATE...

echo [1/4] Downloading latest stats...
python 03_fetch_history.py

echo [2/4] Updating Vegas odds & Defensive Ranks...
python 04_update_features.py

echo [3/4] Cooking the Secret Sauce...
python 07_engineer_secret_sauce.py

echo [4/4] Generating Projections...
python 05_make_projections.py

echo ✅ DONE! Check the 'output' folder.
pause