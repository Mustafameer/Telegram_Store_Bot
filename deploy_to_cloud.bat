@echo off
color 0B
echo ===============================
echo   UPDATING CLOUD SERVER (RAILWAY)
echo ===============================
echo.
echo 1. Adding files...
git add .
echo.
echo 2. Saving changes...
git commit -m "Update Bot Design Rev 15 (Blue Theme)"
echo.
echo 3. Uploading to Cloud...
git push origin main
echo.
echo ===============================
echo   DONE! Server is updating...
echo ===============================
echo Wait 2 minutes then your bot will be live 24/7 with the new design.
echo.
pause
