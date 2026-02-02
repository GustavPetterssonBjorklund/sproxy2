# Removes the tray app from user logon via Task Scheduler
# Run: powershell -ExecutionPolicy Bypass -File .\uninstall_startup.ps1

$ErrorActionPreference = "Stop"

$taskName = "sproxy-tray"

# Check if running as admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "This script requires admin privileges. Requesting elevation..."
    Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $MyInvocation.MyCommand.Path -Wait
    exit
}

# Remove the scheduled task if it exists
if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Startup task '$taskName' removed successfully."
} else {
    Write-Host "Startup task '$taskName' not found."
}
