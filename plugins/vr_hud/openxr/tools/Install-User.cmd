@echo off
setlocal
set "DIR=%~dp0"
set "MANIFEST=%DIR%openxr-api-layer.json"
set "REGKEY=HKCU\Software\Khronos\OpenXR\1\ApiLayers\Implicit"
if not exist "%MANIFEST%" (
  echo [SCAF] ERREUR: manifeste absent.
  exit /b 1
)
rem OpenXR implicit layer registration scoped to the current user.
rem Run only on PCs where local OpenXR API layers are authorized.
reg add "%REGKEY%" /v "%MANIFEST%" /t REG_DWORD /d 0 /f
if errorlevel 1 (
  echo [SCAF] Echec d'enregistrement utilisateur. Voir les restrictions du poste.
  exit /b 1
)
echo [SCAF] Couche OpenXR active pour cet utilisateur.
echo [SCAF] Redemarrer DCS. Conserver le dossier a cet emplacement.
exit /b 0
