# SCAF installer for Windows.
# Run from the repository root; install.bat provides a double-click entry point.
[CmdletBinding()]
param(
    [switch]$SkipUpgrade,
    [switch]$NoVenv
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$root = $PSScriptRoot
$venvPath = Join-Path $root '.venv'

function Fail([string]$message) {
    Write-Host "[ERROR] $message" -ForegroundColor Red
    exit 1
}
function Step([string]$message) {
    Write-Host "`n==> $message" -ForegroundColor Cyan
}
function Invoke-Python([string]$exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) {
        Fail "Python command failed (exit code $LASTEXITCODE): $exe $($arguments -join ' ')"
    }
}

Step 'Checking Python installation'
$pythonExecutable = $null
$pythonPrefixArgs = @()

# Prefer the Windows launcher, but only if it can actually start Python 3.
$pyCommand = Get-Command 'py.exe' -ErrorAction SilentlyContinue
if ($null -ne $pyCommand) {
    & $pyCommand.Source -3 -c 'import sys; print(sys.version)' 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pythonExecutable = $pyCommand.Source
        $pythonPrefixArgs = @('-3')
    }
}

if (-not $pythonExecutable) {
    foreach ($name in @('python.exe', 'python3.exe')) {
        $command = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -eq $command) { continue }
        & $command.Source -c 'import sys; assert sys.version_info.major == 3; print(sys.version)' 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pythonExecutable = $command.Source
            break
        }
    }
}

if (-not $pythonExecutable) {
    Fail 'Python 3 was not found. Install Python 3 from https://www.python.org/downloads/windows/ (enable the Python launcher), then run install.bat again.'
}

if ($NoVenv) {
    Step 'Installing into the selected Python interpreter (NoVenv requested)'
    $pipPython = $pythonExecutable
    $prefix = $pythonPrefixArgs
} else {
    Step 'Creating or reusing .venv'
    $pipPython = Join-Path $venvPath 'Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pipPython -PathType Leaf)) {
        & $pythonExecutable @pythonPrefixArgs -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            Fail 'Could not create .venv. Check that Python includes the venv module.'
        }
    }
    $prefix = @()
}

Step 'Checking pip'
Invoke-Python $pipPython ($prefix + @('-m', 'pip', '--version'))
if (-not $SkipUpgrade) {
    Step 'Updating pip'
    Invoke-Python $pipPython ($prefix + @('-m', 'pip', 'install', '--upgrade', 'pip'))
}

Step 'Discovering requirements.txt files'
$excludedNames = @('.venv', 'venv', 'env', '.git', 'node_modules', '__pycache__', '.tox', '.mypy_cache', '.pytest_cache')
$requirements = @(Get-ChildItem -LiteralPath $root -Filter 'requirements.txt' -File -Recurse | Where-Object {
    $relative = $_.FullName.Substring($root.Length).TrimStart('\', '/')
    $segments = $relative -split '[\\/]'
    -not (@($segments | Where-Object { $excludedNames -contains $_ }).Count -gt 0)
} | Sort-Object FullName)

if ($requirements.Count -eq 0) {
    Write-Host '[INFO] No requirements.txt files were found. Nothing to install.' -ForegroundColor Yellow
} else {
    Write-Host "Found $($requirements.Count) dependency file(s):"
    foreach ($file in $requirements) {
        Write-Host " - $($file.FullName.Substring($root.Length).TrimStart('\', '/'))"
    }
    foreach ($file in $requirements) {
        Step "Installing $($file.FullName.Substring($root.Length).TrimStart('\', '/'))"
        Invoke-Python $pipPython ($prefix + @('-m', 'pip', 'install', '-r', $file.FullName))
    }
}

Step 'Checking installed packages'
Invoke-Python $pipPython ($prefix + @('-m', 'pip', 'check'))

Write-Host "`n========================================" -ForegroundColor Green
Write-Host 'SCAF Python setup completed successfully' -ForegroundColor Green
Write-Host '========================================' -ForegroundColor Green
Write-Host 'UDP: 127.0.0.1:50500 | WebSocket: ws://127.0.0.1:50501'
if (-not $NoVenv) {
    Write-Host "`nLaunch SCAF Core from the repository root:" -ForegroundColor White
    Write-Host '.\.venv\Scripts\python.exe -m core.networking.receiver'
    Write-Host "`nLaunch the live HUD in another terminal:" -ForegroundColor White
    Write-Host '.\.venv\Scripts\python.exe -m plugins.vr_hud.python.src.main --live'
    Write-Host "`nReplay mode:" -ForegroundColor White
    Write-Host '.\.venv\Scripts\python.exe -m plugins.vr_hud.python.src.main "data/sessions/SESSION_ID"'
}
Write-Host "`nNote: This installs Python packages only. DCS, OpenKneeboard, Meta Quest Link and the DCS Export.lua integration must be configured separately." -ForegroundColor Yellow
exit 0
