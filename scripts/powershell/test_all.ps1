<#
.SYNOPSIS
    Full local quality gate for the AI Doctor Follow-Up demo.

.DESCRIPTION
    Runs every check that must pass before a phase is considered locally
    verified, and exits non-zero if any mandated gate fails.

    Gates
      1. Ruff lint + format check on the backend and scripts.
      2. Backend pytest suite (deterministic, offline).
      3. Alembic upgrade -> downgrade -> upgrade smoke test on a temporary DB.
      4. Generated OpenAPI contract check (`/health`, `/version` only).
      5. Frontend TypeScript typecheck, ESLint, Vitest.
      6. Frontend production build.
      7. Optional: Playwright browser smoke test (skipped unless requested AND
         the browser binaries are installed).
      8. Secret/runtime-artifact scan of the tracked files.

    The script reports a real summary: PASS / FAIL / SKIPPED per gate, and the
    overall exit code. It never fabricates a pass.

    EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE

.PARAMETER IncludeE2E
    Also run the Playwright smoke test. Requires `npx playwright install chromium`
    and a running backend; otherwise the gate is reported as SKIPPED.

.PARAMETER BackendOnly
    Run the Python gates only.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\test_all.ps1 -IncludeE2E
#>
[CmdletBinding()]
param(
    [switch]$IncludeE2E,
    [switch]$BackendOnly
)

. "$PSScriptRoot\_common.ps1"

Write-Banner 'test_all: local quality gate'
$startedAt = Get-Date
$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param(
        [string]$Gate,
        [string]$Status,
        [string]$Detail = ''
    )
    $results.Add([pscustomobject]@{ Gate = $Gate; Status = $Status; Detail = $Detail })
    switch ($Status) {
        'PASS' { Write-Ok "$Gate $Detail" }
        'FAIL' { Write-Fail "$Gate $Detail" }
        'SKIP' { Write-Warn "$Gate (skipped) $Detail" }
    }
}

function Get-ExitCodeValue {
    # Tripwire for P1-R06: `Invoke-Native` must return exactly one integer.
    # If a future edit reintroduces pipeline contamination the value becomes an
    # object[] and every gate would silently be classified wrongly, so fail loudly.
    param(
        [Parameter(Mandatory = $true)][string]$Gate,
        [Parameter(Mandatory = $false)]$Value
    )
    if ($Value -is [int]) { return $Value }
    if ($null -eq $Value) {
        Write-Fail "$Gate : command wrapper returned no exit code."
        return 1
    }
    Write-Fail "$Gate : command wrapper returned $($Value.GetType().Name) instead of a numeric exit code."
    return 1
}

function Invoke-Gate {
    param(
        [Parameter(Mandatory = $true)][string]$Gate,
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = $script:RepoRoot
    )
    Write-Step $Gate
    $raw = Invoke-Native -FilePath $FilePath -Arguments $Arguments -WorkingDirectory $WorkingDirectory -AllowFailure
    $code = Get-ExitCodeValue -Gate $Gate -Value $raw
    if ($code -eq 0) {
        Add-Result -Gate $Gate -Status 'PASS'
    }
    else {
        Add-Result -Gate $Gate -Status 'FAIL' -Detail "(exit $code)"
    }
    return $code
}

$venvPython = Get-VenvPython
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Fail "No virtual environment at $(Get-VenvDir). Run setup.ps1 first."
    exit 1
}

# PYTHONPATH lets `alembic`/pytest import `app` without an editable install;
# `setup.ps1` also installs the package editable, so this is belt-and-braces.
$env:PYTHONPATH = $script:BackendDir
$env:APP_ENV = 'test'

# --- 0. command-wrapper self-test (P1-R06) ------------------------------------
# Runs first: if Invoke-Native ever misreports an exit code again, every gate
# below would be classified wrongly, so the harness is validated before use.
$harnessTest = Join-Path $script:ScriptsDir 'tests\invoke_native.tests.ps1'
if (Test-Path -LiteralPath $harnessTest) {
    $powershellExe = (Get-Process -Id $PID).Path
    if (-not $powershellExe) { $powershellExe = 'powershell' }
    Invoke-Gate -Gate 'Command wrapper self-test' -FilePath $powershellExe `
        -Arguments @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $harnessTest) | Out-Null
}
else {
    Add-Result -Gate 'Command wrapper self-test' -Status 'FAIL' -Detail "missing $harnessTest"
}

# --- 0b. shutdown identity self-test (P1-R07) --------------------------------
# Classifier checks for the npm.cmd -> cmd.exe -> node.exe hierarchy. Runs here
# because a wrong identity rule leaks a process on port 5173 after stop.ps1.
$identityTest = Join-Path $script:ScriptsDir 'tests\stop_identity.tests.ps1'
if (Test-Path -LiteralPath $identityTest) {
    $powershellExe = (Get-Process -Id $PID).Path
    if (-not $powershellExe) { $powershellExe = 'powershell' }
    Invoke-Gate -Gate 'Shutdown identity self-test' -FilePath $powershellExe `
        -Arguments @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $identityTest) | Out-Null
}
else {
    Add-Result -Gate 'Shutdown identity self-test' -Status 'FAIL' -Detail "missing $identityTest"
}

# --- 1. Ruff ------------------------------------------------------------------
$ruff = Join-Path (Get-VenvDir) 'Scripts\ruff.exe'
if (-not (Test-Path -LiteralPath $ruff)) {
    $ruff = $venvPython
    $ruffArgs = @('-m', 'ruff', 'check', '.')
    $ruffFormatArgs = @('-m', 'ruff', 'format', '--check', '.')
}
else {
    $ruffArgs = @('check', '.')
    $ruffFormatArgs = @('format', '--check', '.')
}

Invoke-Gate -Gate 'Ruff lint' -FilePath $ruff -Arguments $ruffArgs | Out-Null
Invoke-Gate -Gate 'Ruff format check' -FilePath $ruff -Arguments $ruffFormatArgs | Out-Null

# --- 2. backend tests ---------------------------------------------------------
Invoke-Gate -Gate 'Backend pytest' -FilePath $venvPython -Arguments @('-m', 'pytest', '-q') | Out-Null

# --- 3. alembic smoke ---------------------------------------------------------
Write-Step 'Alembic migration smoke test (upgrade / downgrade / upgrade)'
$smokeDb = Join-Path ([System.IO.Path]::GetTempPath()) ("ai-doctor-alembic-smoke-{0}.db" -f ([guid]::NewGuid().ToString('N')))
$smokeUrl = "sqlite:///$($smokeDb.Replace('\', '/'))"
$alembicOk = $true
$alembicDetail = ''
foreach ($action in @('upgrade:head', 'downgrade:base', 'upgrade:head')) {
    $parts = $action.Split(':')
    $raw = Invoke-Native -FilePath $venvPython `
        -Arguments @('-m', 'alembic', '-c', $script:AlembicIni, '-x', "database_url=$smokeUrl", $parts[0], $parts[1]) `
        -AllowFailure
    $code = Get-ExitCodeValue -Gate "Alembic migration smoke ($action)" -Value $raw
    if ($code -ne 0) {
        $alembicOk = $false
        $alembicDetail = "failed at $action (exit $code)"
        break
    }
}
Remove-Item -LiteralPath $smokeDb -Force -ErrorAction SilentlyContinue
if ($alembicOk) {
    Add-Result -Gate 'Alembic migration smoke' -Status 'PASS'
}
else {
    Add-Result -Gate 'Alembic migration smoke' -Status 'FAIL' -Detail $alembicDetail
}

# --- 4. generated openapi contract -------------------------------------------
Write-Step 'OpenAPI surface check (/health, /version only)'
$openapiScript = Join-Path $script:RepoRoot 'scripts\python\check_openapi.py'
$raw = Invoke-Native -FilePath $venvPython -Arguments @($openapiScript) -AllowFailure
$code = Get-ExitCodeValue -Gate 'OpenAPI surface check' -Value $raw
if ($code -eq 0) {
    Add-Result -Gate 'OpenAPI surface check' -Status 'PASS'
}
else {
    Add-Result -Gate 'OpenAPI surface check' -Status 'FAIL' -Detail "(exit $code)"
}

# --- 5./6. frontend -----------------------------------------------------------
if ($BackendOnly) {
    Add-Result -Gate 'Frontend typecheck' -Status 'SKIP' -Detail '(-BackendOnly)'
    Add-Result -Gate 'Frontend lint' -Status 'SKIP' -Detail '(-BackendOnly)'
    Add-Result -Gate 'Frontend tests' -Status 'SKIP' -Detail '(-BackendOnly)'
    Add-Result -Gate 'Frontend build' -Status 'SKIP' -Detail '(-BackendOnly)'
}
else {
    Assert-CommandExists -Name 'npm.cmd' | Out-Null
    $nodeModules = Join-Path $script:FrontendDir 'node_modules'
    if (-not (Test-Path -LiteralPath $nodeModules)) {
        Add-Result -Gate 'Frontend typecheck' -Status 'FAIL' -Detail 'node_modules missing - run setup.ps1'
        Add-Result -Gate 'Frontend lint' -Status 'FAIL' -Detail 'node_modules missing - run setup.ps1'
        Add-Result -Gate 'Frontend tests' -Status 'FAIL' -Detail 'node_modules missing - run setup.ps1'
        Add-Result -Gate 'Frontend build' -Status 'FAIL' -Detail 'node_modules missing - run setup.ps1'
    }
    else {
        Invoke-Gate -Gate 'Frontend typecheck' -FilePath 'npm.cmd' -Arguments @('run', 'typecheck') -WorkingDirectory $script:FrontendDir | Out-Null
        Invoke-Gate -Gate 'Frontend lint' -FilePath 'npm.cmd' -Arguments @('run', 'lint') -WorkingDirectory $script:FrontendDir | Out-Null
        Invoke-Gate -Gate 'Frontend tests' -FilePath 'npm.cmd' -Arguments @('run', 'test') -WorkingDirectory $script:FrontendDir | Out-Null
        Invoke-Gate -Gate 'Frontend build' -FilePath 'npm.cmd' -Arguments @('run', 'build') -WorkingDirectory $script:FrontendDir | Out-Null
    }
}

# --- 7. optional browser smoke ------------------------------------------------
if ($IncludeE2E -and -not $BackendOnly) {
    Write-Step 'Playwright browser smoke test'
    $browsersPath = Join-Path $env:USERPROFILE 'AppData\Local\ms-playwright'
    if (-not (Test-Path -LiteralPath $browsersPath)) {
        Add-Result -Gate 'Playwright smoke' -Status 'SKIP' -Detail 'browser binaries not installed (npx playwright install chromium)'
    }
    elseif (-not (Test-PortListening -Port $script:BackendPort)) {
        Add-Result -Gate 'Playwright smoke' -Status 'SKIP' -Detail 'backend not running (start.ps1)'
    }
    else {
        Invoke-Gate -Gate 'Playwright smoke' -FilePath 'npm.cmd' -Arguments @('run', 'test:e2e') -WorkingDirectory $script:FrontendDir | Out-Null
    }
}
else {
    Add-Result -Gate 'Playwright smoke' -Status 'SKIP' -Detail '(use -IncludeE2E; requires browser binaries and a running backend)'
}

# --- 8. secret / artifact scan ------------------------------------------------
Write-Step 'Secret and runtime-artifact scan of tracked files'
$scanScript = Join-Path $script:RepoRoot 'scripts\python\scan_repository.py'
$raw = Invoke-Native -FilePath $venvPython -Arguments @($scanScript) -AllowFailure
$code = Get-ExitCodeValue -Gate 'Secret/artifact scan' -Value $raw
if ($code -eq 0) {
    Add-Result -Gate 'Secret/artifact scan' -Status 'PASS'
}
else {
    Add-Result -Gate 'Secret/artifact scan' -Status 'FAIL' -Detail "(exit $code)"
}

# --- summary ------------------------------------------------------------------
$elapsed = [math]::Round(((Get-Date) - $startedAt).TotalSeconds, 1)
Write-Host ''
Write-Host ('-' * 74) -ForegroundColor DarkGray
Write-Host '  Quality gate summary' -ForegroundColor White
Write-Host ('-' * 74) -ForegroundColor DarkGray
foreach ($result in $results) {
    $colour = switch ($result.Status) {
        'PASS' { 'Green' }
        'FAIL' { 'Red' }
        default { 'Yellow' }
    }
    Write-Host ("  {0,-28} {1,-6} {2}" -f $result.Gate, $result.Status, $result.Detail) -ForegroundColor $colour
}
Write-Host ('-' * 74) -ForegroundColor DarkGray

$failed = @($results | Where-Object { $_.Status -eq 'FAIL' })
$passed = @($results | Where-Object { $_.Status -eq 'PASS' })
$skipped = @($results | Where-Object { $_.Status -eq 'SKIP' })

Write-Host ("  PASS {0}   FAIL {1}   SKIPPED {2}   ({3}s)" -f $passed.Count, $failed.Count, $skipped.Count, $elapsed)
Write-Host ''

if ($failed.Count -gt 0) {
    Write-Host 'test_all result: FAIL' -ForegroundColor Red
    exit 1
}

Write-Host 'test_all result: PASS' -ForegroundColor Green
if ($skipped.Count -gt 0) {
    Write-Host 'Skipped gates are listed above and are NOT counted as passes.' -ForegroundColor Yellow
}
exit 0
