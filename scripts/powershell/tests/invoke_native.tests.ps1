<#
.SYNOPSIS
    Executable regression tests for `Invoke-Native` (P1-R06).

.DESCRIPTION
    The Windows quality gate (`test_all.ps1`) reported PASS 1 / FAIL 9 while the
    underlying commands succeeded, because `Invoke-Native` emitted the native
    command's stdout into its caller's pipeline together with the exit code.
    `$code = Invoke-Native ...` then produced a multi-element array and
    `$code -eq 0` was false for a successful command.

    This script proves the wrapper now returns exactly one integer for:
      1. a successful command that prints output,
      2. a silent successful command,
      3. a failing command with output and a non-zero exit code,
      4. a command whose *output* looks like a number (no confusion with the code),
      5. the -AllowFailure path (returns the code instead of throwing).

    It also checks that visible output is still produced, so the fix cannot be
    "silence the tool".

    Exit code: 0 when every case passes, 1 otherwise.

.NOTES
    Runs on Windows PowerShell 5.1 and PowerShell 7+.

    From the repository root:
        powershell -NoProfile -ExecutionPolicy Bypass `
            -File .\scripts\powershell\tests\invoke_native.tests.ps1

    EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
#>
[CmdletBinding()]
param()

. "$PSScriptRoot\..\_common.ps1"

$script:Failures = 0
$script:Cases = 0

function Assert-True {
    param(
        [Parameter(Mandatory = $true)][bool]$Condition,
        [Parameter(Mandatory = $true)][string]$Message
    )
    $script:Cases++
    if ($Condition) {
        Write-Host "  PASS  $Message" -ForegroundColor Green
    }
    else {
        Write-Host "  FAIL  $Message" -ForegroundColor Red
        $script:Failures++
    }
}

function Test-SingleInteger {
    param(
        [Parameter(Mandatory = $false)]$Value,
        [Parameter(Mandatory = $true)][string]$Label
    )
    Assert-True -Condition ($Value -is [int]) -Message "$Label returns a single [int] (got $(if ($null -eq $Value) { '<null>' } else { $Value.GetType().Name }))"
}

Write-Host ''
Write-Host 'Invoke-Native regression tests (P1-R06)' -ForegroundColor Cyan
Write-Host 'EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE' -ForegroundColor Yellow
Write-Host ''

# The probes are the running interpreter itself: no external dependency, and the
# behaviour under test is the wrapper, not the tool it launches.
$probe = (Get-Process -Id $PID).Path
if (-not $probe) {
    $probe = (Get-Command -Name 'powershell' -ErrorAction SilentlyContinue).Source
}
if (-not $probe) {
    Write-Host '  FAIL  could not locate a host executable for the probes' -ForegroundColor Red
    exit 1
}
Write-Host "  host executable: $probe" -ForegroundColor DarkGray
Write-Host ''

# --- case 1: successful command that prints output ----------------------------
Write-Host '[1] successful command that prints output' -ForegroundColor White
$outputProbe = 'Write-Output "All checks passed!"'
$result = Invoke-Native -FilePath $probe -Arguments @('-NoProfile', '-Command', $outputProbe) -AllowFailure
Test-SingleInteger -Value $result -Label 'exit code'
Assert-True -Condition ($result -eq 0) -Message 'successful command reports exit code 0'

# --- case 2: silent successful command ---------------------------------------
Write-Host '[2] silent successful command' -ForegroundColor White
$silentResult = Invoke-Native -FilePath $probe -Arguments @('-NoProfile', '-Command', 'exit 0') -AllowFailure
Test-SingleInteger -Value $silentResult -Label 'exit code'
Assert-True -Condition ($silentResult -eq 0) -Message 'silent command reports exit code 0'

# --- case 3: failing command with output and non-zero exit -------------------
Write-Host '[3] failing command with output and a non-zero exit code' -ForegroundColor White
$failProbe = 'Write-Output "some failure detail"; exit 7'
$failResult = Invoke-Native -FilePath $probe -Arguments @('-NoProfile', '-Command', $failProbe) -AllowFailure
Test-SingleInteger -Value $failResult -Label 'exit code'
Assert-True -Condition ($failResult -eq 7) -Message 'failing command reports exit code 7, not the output text'

# --- case 4: output that looks numeric ---------------------------------------
Write-Host '[4] command whose output looks like a number' -ForegroundColor White
$numericProbe = 'Write-Output "0"; Write-Output "99"; exit 3'
$numericResult = Invoke-Native -FilePath $probe -Arguments @('-NoProfile', '-Command', $numericProbe) -AllowFailure
Test-SingleInteger -Value $numericResult -Label 'exit code'
Assert-True -Condition ($numericResult -eq 3) -Message 'numeric-looking output does not leak into the exit code'

# --- case 5: -AllowFailure is not needed for success; throwing path still works -
Write-Host '[5] failure without -AllowFailure still throws' -ForegroundColor White
$threw = $false
try {
    Invoke-Native -FilePath $probe -Arguments @('-NoProfile', '-Command', 'exit 5') | Out-Null
}
catch {
    $threw = $true
    Assert-True -Condition ($_.Exception.Message -match 'exit 5') -Message 'exception message names the exit code'
}
Assert-True -Condition $threw -Message 'a failing command without -AllowFailure terminates the caller'

# --- case 6: visible output is preserved -------------------------------------
# `Out-Host` writes to the real console, which a redirect inside this same
# process cannot capture. The probe therefore runs in a CHILD process whose
# stdout is captured: if the marker is there, human output survived the fix.
Write-Host '[6] visible output is preserved (the fix does not silence tools)' -ForegroundColor White
$hostProbeScript = Join-Path ([System.IO.Path]::GetTempPath()) ("invoke-native-probe-{0}.ps1" -f ([guid]::NewGuid().ToString('N')))
$commonPath = Join-Path $PSScriptRoot '..\_common.ps1'
# Single-quoted here-string: nothing is expanded by accident, then the two
# paths are substituted explicitly (they may contain spaces or `$`).
$hostProbeBody = @'
. '__COMMON__'
Invoke-Native -FilePath '__HOST__' -Arguments @('-NoProfile', '-Command', 'Write-Output "VISIBLE-MARKER-12345"') -AllowFailure | Out-Null
exit 0
'@
$hostProbeBody = $hostProbeBody.Replace('__COMMON__', $commonPath).Replace('__HOST__', $probe)
try {
    Set-Content -LiteralPath $hostProbeScript -Value $hostProbeBody -Encoding UTF8
    $childOutput = (& $probe -NoProfile -ExecutionPolicy Bypass -File $hostProbeScript 2>&1 | Out-String)
}
finally {
    Remove-Item -LiteralPath $hostProbeScript -Force -ErrorAction SilentlyContinue
}
Assert-True -Condition ($childOutput -match 'VISIBLE-MARKER-12345') -Message 'command output still reaches the console'
Assert-True -Condition ($childOutput -notmatch 'Exception|ParserError') -Message 'probe process ran without a PowerShell error'

# --- case 7: Get-NativeOutput keeps its capture semantics --------------------
Write-Host '[7] Get-NativeOutput still captures stdout separately' -ForegroundColor White
$capturedResult = Get-NativeOutput -FilePath $probe -Arguments @('-NoProfile', '-Command', 'Write-Output "captured-text"; exit 0')
Assert-True -Condition ($capturedResult.Output -eq 'captured-text') -Message 'Get-NativeOutput returns the captured text'
Assert-True -Condition ($capturedResult.ExitCode -eq 0) -Message 'Get-NativeOutput reports the exit code'

# --- summary ------------------------------------------------------------------
Write-Host ''
Write-Host ('-' * 74) -ForegroundColor DarkGray
if ($script:Failures -gt 0) {
    Write-Host ("Invoke-Native tests: FAIL ({0} of {1} checks failed)" -f $script:Failures, $script:Cases) -ForegroundColor Red
    exit 1
}
Write-Host ("Invoke-Native tests: PASS ({0} checks)" -f $script:Cases) -ForegroundColor Green
exit 0
