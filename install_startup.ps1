# Registers the tray app to run at user logon via Task Scheduler
# Run: powershell -ExecutionPolicy Bypass -File .\install_startup.ps1

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$mainPath = Join-Path $scriptDir "main.py"

# Find pythonw.exe (no console window). Fallback to python.exe if not found.
$pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1

if (-not $pythonw) {
    $pythonw = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source -First 1
}

if (-not $pythonw) {
    throw "Python not found in PATH. Install Python or add it to PATH."
}

$taskName = "sproxy-tray"
$action = New-ScheduledTaskAction -Execute $pythonw -Argument ""$mainPath"" -WorkingDirectory $scriptDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Hidden

# Remove existing task if present
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null

Write-Host "Startup task '$taskName' registered. It will run on next logon."
