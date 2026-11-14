<#
.SYNOPSIS
    Reproducible local installation for the AI Doctor Follow-Up demo.

.DESCRIPTION
    Idempotent setup, safe to re-run:

      1. Create `.env` from `.env.example` when missing (never overwrites).
      2. Create the Python 3.12 virtual environment (default `<repo>\.venv`,
         override with $env:APP_VENV_DIR - the owner keeps dependencies on E:).
      3. Install the pinned, hash-verified lock files.
      4. Install the backend package in editable mode (for `app` imports).
      5. Create `data/runtime/` and apply the Alembic baseline migration.
      6. Install frontend dependencies with `npm.cmd ci` / `npm.cmd install`.

    No secret is created, nothing is downloaded from anywhere except the official
    package registries, and no process is started.

    EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE

.PARAMETER SkipFrontend
    Install only the Python side.

.PARAMETER SkipDatabase
    Create the virtual environment and install dependencies, but do not migrate.

.PARAMETER Clean
    Delete the existing virtual environment and node_modules first (a full
    reinstall). `data/runtime` is never deleted by this script.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\setup.ps1

.EXAMPLE
    $env:APP_VENV_DIR = 'E:\AI-Doctor-FollowUp-Agent\.venv'
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\setup.ps1
#>
[CmdletBinding()]
param(
    [switch]$SkipFrontend,
    [switch]$SkipDatabase,
    [switch]$Clean
)

. "$PSScriptRoot\_common.ps1"

Write-Banner 'Setup: reproducible local installation'
$startedAt = Get-Date
$step = 0

try {
    # --- 0. preconditions -----------------------------------------------------
    $step++
    Write-Step "[$step] Verifying Python 3.12"
    Assert-CommandExists -Name 'py' | Out-Null
    $pythonVersion = Assert-Python312 -Version (Get-PythonVersionFromLauncher)
    Write-Ok "Python $pythonVersion"

    # --- 1. .env --------------------------------------------------------------
    $step++
    Write-Step "[$step] Local configuration (.env)"
    $envFile = Join-Path $script:RepoRoot '.env'
    $envExample = Join-Path $script:RepoRoot '.env.example'
    if (Test-Path -LiteralPath $envFile) {
        Write-Ok '.env already exists (left untouched)'
    }
    else {
        if (-not (Test-Path -LiteralPath $envExample)) {
            throw ".env.example is missing from $($script:RepoRoot); the repository is incomplete."
        }
        Copy-Item -LiteralPath $envExample -Destination $envFile
        Write-Ok '.env created from .env.example'
    }

    # --- 2. virtual environment ----------------------------------------------
    $step++
    $venvDir = Get-VenvDir
    Write-Step "[$step] Python virtual environment at $venvDir"
    if ($Clean -and (Test-Path -LiteralPath $venvDir)) {
        Remove-Item -LiteralPath $venvDir -Recurse -Force
        Write-Ok 'Existing virtual environment removed (-Clean)'
    }
    if (Test-Path -LiteralPath (Get-VenvPython)) {
        Write-Ok 'Virtual environment already present'
    }
    else {
        $parent = Split-Path -Parent $venvDir
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Invoke-Native -FilePath 'py' -Arguments @('-3.12', '-m', 'venv', $venvDir) | Out-Null
        Write-Ok 'Virtual environment created'
    }

    $venvPython = Get-VenvPython
    $venvVersionResult = Get-NativeOutput -FilePath $venvPython -Arguments @('-c', "import sys;print('%d.%d.%d' % sys.version_info[:3])")
    if ($venvVersionResult.ExitCode -ne 0) {
        throw "The virtual environment interpreter failed to run: $venvPython"
    }
    Assert-Python312 -Version $venvVersionResult.Output | Out-Null
    Write-Ok "venv interpreter: Python $($venvVersionResult.Output)"

    # --- 3. python dependencies ----------------------------------------------
    $step++
    Write-Step "[$step] Installing hash-pinned Python dependencies"
    Invoke-Native -FilePath $venvPython -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip', '--disable-pip-version-check', '--quiet') | Out-Null
    $runtimeLock = Join-Path $script:RepoRoot 'requirements\requirements.lock'
    $devLock = Join-Path $script:RepoRoot 'requirements\requirements-dev.lock'
    foreach ($lock in @($runtimeLock, $devLock)) {
        if (-not (Test-Path -LiteralPath $lock)) {
            throw "Lock file missing: $lock"
        }
    }
    Invoke-Native -FilePath $venvPython -Arguments @(
        '-m', 'pip', 'install', '--require-hashes', '--no-deps',
        '--disable-pip-version-check', '--quiet', '-r', $runtimeLock
    ) | Out-Null
    Write-Ok 'Runtime lock files installed with --require-hashes'

    Invoke-Native -FilePath $venvPython -Arguments @(
        '-m', 'pip', 'install', '--require-hashes', '--no-deps',
        '--disable-pip-version-check', '--quiet', '-r', $devLock
    ) | Out-Null
    Write-Ok 'Development lock files installed with --require-hashes'

    # --- 4. backend package ---------------------------------------------------
    $step++
    Write-Step "[$step] Installing the backend package (editable)"
    Invoke-Native -FilePath $venvPython -Arguments @(
        '-m', 'pip', 'install', '--no-build-isolation', '--no-deps',
        '--disable-pip-version-check', '--quiet', '-e', $script:RepoRoot
    ) | Out-Null
    Invoke-Native -FilePath $venvPython -Arguments @('-c', 'import app; print(app.__version__)') | Out-Null
    Write-Ok 'Backend package importable (app.__version__)'

    # --- 5. database ----------------------------------------------------------
    $step++
    if ($SkipDatabase) {
        Write-Warn 'Database migration skipped (-SkipDatabase)'
    }
    else {
        Write-Step "[$step] Creating the SQLite database and applying migrations"
        Ensure-RuntimeDir | Out-Null
        Invoke-Native -FilePath $venvPython -Arguments @(
            '-m', 'alembic', '-c', $script:AlembicIni, 'upgrade', 'head'
        ) | Out-Null
        Write-Ok 'Alembic migrations applied (head)'
    }

    # --- 6. frontend ----------------------------------------------------------
    $step++
    if ($SkipFrontend) {
        Write-Warn 'Frontend installation skipped (-SkipFrontend)'
    }
    else {
        Write-Step "[$step] Installing frontend dependencies (npm.cmd)"
        Assert-CommandExists -Name 'npm.cmd' | Out-Null
        if ($Clean) {
            $nodeModules = Join-Path $script:FrontendDir 'node_modules'
            if (Test-Path -LiteralPath $nodeModules) {
                Remove-Item -LiteralPath $nodeModules -Recurse -Force
                Write-Ok 'node_modules removed (-Clean)'
            }
        }
        $lockFile = Join-Path $script:FrontendDir 'package-lock.json'
        if (Test-Path -LiteralPath $lockFile) {
            Invoke-Native -FilePath 'npm.cmd' -Arguments @('ci', '--no-audit', '--no-fund') -WorkingDirectory $script:FrontendDir | Out-Null
            Write-Ok 'npm ci completed from package-lock.json'
        }
        else {
            Invoke-Native -FilePath 'npm.cmd' -Arguments @('install', '--no-audit', '--no-fund') -WorkingDirectory $script:FrontendDir | Out-Null
            Write-Ok 'npm install completed (no lock file was present)'
        }
    }

    # --- summary --------------------------------------------------------------
    $elapsed = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 1)
    Write-Host ''
    Write-Host "Setup result: PASS (${elapsed}s)" -ForegroundColor Green
    Write-Host ''
    Write-Host 'Next steps:' -ForegroundColor Cyan
    Write-Host '  Run the quality gate : powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1'
    Write-Host '  Start the application: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1'
    Write-Host '  Stop  the application: powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\stop.ps1'
    exit 0
}
catch {
    Write-Host ''
    Write-Fail "Setup failed at step $step."
    Write-Fail $_.Exception.Message
    Write-Host ''
    Write-Host 'Nothing outside the repository was modified. Fix the reported problem and re-run setup.ps1.' -ForegroundColor Yellow
    exit 1
}
