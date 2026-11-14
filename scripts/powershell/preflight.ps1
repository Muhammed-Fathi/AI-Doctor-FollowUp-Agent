<#
.SYNOPSIS
    Read-only environment check for the AI Doctor Follow-Up local demo.

.DESCRIPTION
    Verifies that this machine can build, test and run the project, and reports
    exactly what is missing. It changes nothing: no install, no download, no
    process start, no file write.

    Checks
      1. Python 3.12 is reachable through the `py -3.12` launcher.
      2. pip is available for that interpreter.
      3. Node.js and the npm CLI (npm.cmd works even when npm.ps1 is blocked).
      4. git is available.
      5. Free disk space for dependencies and the SQLite database.
      6. Whether the pinned dependencies / node_modules are already installed.
      7. Whether ports 8000 / 5173 are already in use.

    Exit codes
      0  all mandatory checks passed
      1  at least one mandatory check failed (details printed above)

    EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE

.PARAMETER SkipPortChecks
    Skip the TCP port probe (useful on CI or when intentionally running twice).

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\preflight.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipPortChecks
)

. "$PSScriptRoot\_common.ps1"

Write-Banner 'Preflight: environment readiness check (read-only)'
Write-Host "Repository root : $script:RepoRoot"
Write-Host "PowerShell      : $($PSVersionTable.PSVersion)"
Write-Host ''

$failures = New-Object System.Collections.Generic.List[string]
$warnings = New-Object System.Collections.Generic.List[string]

# --- 1. Python 3.12 -----------------------------------------------------------
Write-Step 'Python 3.12 (via py -3.12)'
$pythonVersion = $null
if (Get-Command -Name 'py' -ErrorAction SilentlyContinue) {
    $pythonVersion = Get-PythonVersionFromLauncher
}
if ($pythonVersion) {
    try {
        $checked = Assert-Python312 -Version $pythonVersion
        Write-Ok "py -3.12 -> Python $checked"
    }
    catch {
        $failures.Add($_.Exception.Message)
        Write-Fail $_.Exception.Message
    }
}
else {
    $message = 'Python 3.12 not found through `py -3.12`. Install Python 3.12 with the Python Launcher, and never use the machine default (`python`, 3.14) for this project.'
    $failures.Add($message)
    Write-Fail $message
}

# --- 2. pip -------------------------------------------------------------------
Write-Step 'pip for Python 3.12'
if ($pythonVersion) {
    $pipResult = Get-NativeOutput -FilePath 'py' -Arguments @('-3.12', '-m', 'pip', '--version')
    if ($pipResult.ExitCode -eq 0 -and $pipResult.Output) {
        Write-Ok $pipResult.Output
    }
    else {
        $message = 'pip is not available for Python 3.12. Run: py -3.12 -m ensurepip --upgrade'
        $failures.Add($message)
        Write-Fail $message
    }
}
else {
    Write-Warn 'Skipped because Python 3.12 was not found.'
}

# --- 3. Node.js and the npm CLI -----------------------------------------------
Write-Step 'Node.js and npm'
$nodeCommand = Get-Command -Name 'node' -ErrorAction SilentlyContinue
if ($nodeCommand) {
    $nodeResult = Get-NativeOutput -FilePath 'node' -Arguments @('--version')
    if ($nodeResult.ExitCode -eq 0) {
        Write-Ok "node $($nodeResult.Output)"
        if (-not (Test-NodeVersion -Version $nodeResult.Output)) {
            $message = "Node.js $($nodeResult.Output) does not satisfy Vite 7 (requires ^20.19.0 or >=22.12.0)."
            $failures.Add($message)
            Write-Fail $message
        }
    }
    else {
        $message = 'node --version failed.'
        $failures.Add($message)
        Write-Fail $message
    }
}
else {
    $message = 'Node.js is not on PATH. Install Node.js 22 LTS or newer.'
    $failures.Add($message)
    Write-Fail $message
}

# npm: prefer npm.cmd because npm.ps1 can be blocked by the execution policy.
$npmCmd = Get-Command -Name 'npm.cmd' -ErrorAction SilentlyContinue
if ($npmCmd) {
    $npmResult = Get-NativeOutput -FilePath 'npm.cmd' -Arguments @('--version')
    if ($npmResult.ExitCode -eq 0) {
        Write-Ok "npm.cmd $($npmResult.Output)"
    }
    else {
        $message = 'npm.cmd --version failed.'
        $failures.Add($message)
        Write-Fail $message
    }
}
else {
    $message = 'npm.cmd was not found. It ships with Node.js; check your Node installation.'
    $failures.Add($message)
    Write-Fail $message
}

$npmPs1 = Get-Command -Name 'npm.ps1' -ErrorAction SilentlyContinue
if ($npmPs1) {
    Write-Host '      note: npm.ps1 exists; these scripts use npm.cmd so the execution policy does not need changing.' -ForegroundColor DarkGray
}

# --- 4. git -------------------------------------------------------------------
Write-Step 'git'
if (Get-Command -Name 'git' -ErrorAction SilentlyContinue) {
    $gitResult = Get-NativeOutput -FilePath 'git' -Arguments @('--version')
    if ($gitResult.ExitCode -eq 0) {
        Write-Ok $gitResult.Output
    }
    else {
        $warnings.Add('git --version failed; version detection will report "unknown".')
        Write-Warn 'git --version failed; /version will report "unknown".'
    }
}
else {
    $warnings.Add('git is not on PATH; /version will report git_sha "unknown".')
    Write-Warn 'git is not on PATH; /version will report git_sha "unknown".'
}

# --- 5. disk space ------------------------------------------------------------
Write-Step 'Free disk space'
$targetForSpace = Get-VenvDir
$driveLetter = (Split-Path -Qualifier $script:RepoRoot)
if ($targetForSpace) {
    $targetDrive = Split-Path -Qualifier $targetForSpace -ErrorAction SilentlyContinue
    if ($targetDrive) { $driveLetter = $targetDrive }
}
try {
    $drive = Get-PSDrive -Name ($driveLetter.TrimEnd(':')) -ErrorAction Stop
    $freeGb = [math]::Round($drive.Free / 1GB, 2)
    if ($freeGb -lt 2) {
        $message = "Only $freeGb GB free on $driveLetter. At least 2 GB is recommended for dependencies and the database."
        $failures.Add($message)
        Write-Fail $message
    }
    elseif ($freeGb -lt 5) {
        $warnings.Add("$freeGb GB free on $driveLetter; 5 GB or more is recommended.")
        Write-Warn "$freeGb GB free on $driveLetter (5 GB+ recommended)."
    }
    else {
        Write-Ok "$freeGb GB free on $driveLetter"
    }
}
catch {
    $warnings.Add("Could not read free space for $driveLetter.")
    Write-Warn "Could not read free space for $driveLetter."
}

# --- 6. installed state -------------------------------------------------------
Write-Step 'Dependency state (informational)'
$venvPython = Get-VenvPython
if (Test-Path -LiteralPath $venvPython) {
    Write-Ok "Python virtual environment present: $(Get-VenvDir)"
}
else {
    Write-Warn "No virtual environment at $(Get-VenvDir) - run setup.ps1."
}

if (Test-Path -LiteralPath (Join-Path $script:FrontendDir 'node_modules')) {
    Write-Ok 'frontend/node_modules present'
}
else {
    Write-Warn 'frontend/node_modules missing - run setup.ps1.'
}

if (Test-Path -LiteralPath (Join-Path $script:RepoRoot '.env')) {
    Write-Ok '.env present'
}
else {
    Write-Warn '.env missing - setup.ps1 creates it from .env.example.'
}

# --- 7. ports -----------------------------------------------------------------
if (-not $SkipPortChecks) {
    Write-Step 'Port availability (loopback)'
    foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
        if (Test-PortListening -Port $port) {
            $warnings.Add("Port $port is already in use; a previous run may still be active (stop.ps1).")
            Write-Warn "Port $port is already in use."
        }
        else {
            Write-Ok "Port $port is free."
        }
    }
}

# --- summary ------------------------------------------------------------------
Write-Host ''
if ($failures.Count -eq 0) {
    Write-Host 'Preflight result: PASS - mandatory prerequisites are satisfied.' -ForegroundColor Green
    if ($warnings.Count -gt 0) {
        Write-Host "Warnings: $($warnings.Count)" -ForegroundColor Yellow
        foreach ($warning in $warnings) { Write-Warn $warning }
    }
    Write-Host 'Next step: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\setup.ps1'
    exit 0
}

Write-Host "Preflight result: FAIL - $($failures.Count) mandatory check(s) failed." -ForegroundColor Red
foreach ($failure in $failures) { Write-Fail $failure }
if ($warnings.Count -gt 0) {
    foreach ($warning in $warnings) { Write-Warn $warning }
}
exit 1
