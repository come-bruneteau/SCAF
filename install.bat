@echo off
setlocal
cd /d "%~dp0"
echo.
echo ========================================
echo        SCAF - Windows Setup
 echo ========================================
echo.
where powershell.exe >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Windows PowerShell is not available.
    pause
    exit /b 1
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" (
    echo [ERROR] Setup failed with error code %RESULT%.
) else (
    echo [OK] Setup completed.
)
echo.
pause
exit /b %RESULT%
