# Windows PowerShell Installer for local-code (lc)
$ErrorActionPreference = "Stop"

$InstallDir = "$HOME\.local\bin"
if (!(Test-Path -Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
}

$ScriptUrl = "https://raw.githubusercontent.com/shoryasrivastava388-sys/local-code/main/local_code.py"
$TargetPy = "$InstallDir\local_code.py"

Write-Host "→ Downloading local-code to $InstallDir..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $ScriptUrl -OutFile $TargetPy -UseBasicParsing

# Create Windows .cmd wrappers so 'lc', 'local-code', 'qc', and 'qwen-agent' run directly from CMD / PowerShell
$CmdContent = "@echo off`r`npython `"$TargetPy`" %*"
Set-Content -Path "$InstallDir\lc.cmd" -Value $CmdContent
Set-Content -Path "$InstallDir\local-code.cmd" -Value $CmdContent
Set-Content -Path "$InstallDir\qc.cmd" -Value $CmdContent
Set-Content -Path "$InstallDir\qwen-agent.cmd" -Value $CmdContent

Write-Host "✓ Successfully installed local-code (lc) to $InstallDir" -ForegroundColor Green
Write-Host ""
Write-Host "Make sure $InstallDir is in your User PATH environment variable." -ForegroundColor Yellow
Write-Host "To add it permanently in PowerShell, run:" -ForegroundColor Yellow
Write-Host "  [Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';$InstallDir', 'User')" -ForegroundColor Gray
Write-Host ""
Write-Host "Usage:"
Write-Host "  lc                 # Interactive mode"
Write-Host "  lc -y 'Your task'  # Auto-approve mode"
