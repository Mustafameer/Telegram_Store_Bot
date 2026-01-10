@echo off
chcp 65001 >nul
echo ============================================
echo   Creating Telegram Store App Installer
echo ============================================
echo.

cd /d "%~dp0"

:: Check if application is built
if not exist "build\windows\x64\runner\Release\flutter_store_app.exe" (
    echo Error: Application not built yet!
    echo Please run 'build_release.bat' first to build the application.
    pause
    exit /b 1
)

echo Application found!
echo.

:: Find Inno Setup
set INNO_SETUP_PATH=
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set INNO_SETUP_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set INNO_SETUP_PATH=C:\Program Files\Inno Setup 6\ISCC.exe
)

if "%INNO_SETUP_PATH%"=="" (
    echo Error: Inno Setup not found!
    echo.
    echo Please install Inno Setup 6 from:
    echo https://jrsoftware.org/isdl.php
    echo.
    echo Or manually compile 'build_installer.iss' using Inno Setup Compiler.
    pause
    exit /b 1
)

echo Found Inno Setup at: %INNO_SETUP_PATH%
echo.

:: Create installer directory
if not exist "installer" mkdir installer

:: Compile installer
echo Compiling installer...
echo.

pushd "%~dp0"
"%INNO_SETUP_PATH%" "%~dp0build_installer.iss"
popd

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================
    echo   Installer created successfully!
    echo ============================================
    echo.
    if exist "installer\TelegramStoreApp_Setup.exe" (
        echo Installer location: installer\TelegramStoreApp_Setup.exe
        echo.
        echo You can now distribute this installer file.
    ) else (
        echo Warning: Installer file not found at expected location.
    )
) else (
    echo.
    echo Error: Failed to create installer!
    echo Exit code: %ERRORLEVEL%
)

echo.
pause
