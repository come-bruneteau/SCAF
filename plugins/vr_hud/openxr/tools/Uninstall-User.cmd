@echo off
setlocal
set "MANIFEST=%~dp0openxr-api-layer.json"
set "REGKEY=HKCU\Software\Khronos\OpenXR\1\ApiLayers\Implicit"
rem Remove only the value registered for this exact package path.
reg delete "%REGKEY%" /v "%MANIFEST%" /f
if errorlevel 1 (
  echo [SCAF] Enregistrement introuvable ou suppression refusee.
  exit /b 1
)
echo [SCAF] Couche OpenXR desactivee pour cet utilisateur.
exit /b 0
