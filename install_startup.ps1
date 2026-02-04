# Registers the SProxy2 tray app to run at user logon (Task Scheduler)
# Run: powershell -ExecutionPolicy Bypass -File .\install_startup.ps1

$ErrorActionPreference = "Stop"

# --- Elevation check (Task Scheduler registration can require admin) ---
$isAdmin = ([Security.Principal.WindowsPrincipal]
    [Security.Principal.WindowsIdentity]::GetCurrent()
).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "Elevation required. Relaunching as admin..."
    Start-Process powershell -Verb RunAs -ArgumentList `
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$($MyInvocation.MyCommand.Path)`""
    exit
}

# --- Paths ---
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainPath  = Join-Path $scriptDir "main.py"

$venvPythonW = Join-Path $scriptDir ".venv\Scripts\pythonw.exe"
$venvPython  = Join-Path $scriptDir ".venv\Scripts\python.exe"

if (Test-Path $venvPythonW) {
    $python = $venvPythonW
} elseif (Test-Path $venvPython) {
    $python = $venvPython
} else {
    throw "Virtualenv not found. Expected .venv\Scripts\python(w).exe in $scriptDir"
}

if (-not (Test-Path $mainPath)) {
    throw "main.py not found at $mainPath"
}

# --- Task config ---
$taskName  = "sproxy-tray"

$action = New-ScheduledTaskAction `
    -Execute "`"$python`"" `
    -Argument "`"$mainPath`"" `
    -WorkingDirectory "`"$scriptDir`""

$trigger = New-ScheduledTaskTrigger -AtLogOn

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -Hidden `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

# --- Replace existing task ---
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName  $taskName `
    -Action   $action `
    -Trigger  $trigger `
    -Principal $principal `
    -Settings $settings `
    | Out-Null

Write-Host "✔ Startup task '$taskName' installed"
Write-Host "  Python : $python"
Write-Host "  Script : $mainPath"