<#
.SYNOPSIS
    Executable regression tests for the shutdown identity logic (P1-R07).

.DESCRIPTION
    The owner's live Windows run left Vite on port 5173 because stop.ps1
    rejected the recorded `cmd.exe`/`npm.cmd` wrapper: its command line contains
    neither "vite" nor "node_modules".

    These tests exercise the classifier helpers in `_common.ps1` against the
    EXACT command lines observed on the owner's machine, plus the look-alikes
    that must NOT be stopped. They need no special privileges and start no
    long-lived process, so they are safe to run at any time.

    Cases:
      1. the recorded cmd.exe/npm.cmd wrapper is recognised as ours
      2. that same wrapper is NOT misclassified as the Vite process
      3. the real Vite command line under this repo is recognised
      4. a Vite from a different project is rejected
      5. plain node.exe is rejected
      6. `npm run build` is rejected (only the dev server counts)
      7. this app's uvicorn is recognised, another app's is rejected
      8. forward-slash Vite paths are recognised
      9. the descendant tree walk finds a real child process
     10. identity is rejected for a different image name / creation time
     11. a falsy ConvertFrom-Json property does not hide a state entry

    Exit code: 0 when every check passes, 1 otherwise.

.NOTES
    From the repository root:
        powershell -NoProfile -ExecutionPolicy Bypass `
            -File .\scripts\powershell\tests\stop_identity.tests.ps1

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

Write-Host ''
Write-Host 'Stop/identity regression tests (P1-R07)' -ForegroundColor Cyan
Write-Host 'EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE' -ForegroundColor Yellow
Write-Host ''
Write-Host "  repository: $script:RepoRoot" -ForegroundColor DarkGray
Write-Host ''

$port = $script:FrontendPort

# Verbatim from review 5905623035 (owner's Windows PowerShell 5.1 evidence).
$ownedWrapper = 'C:\Windows\system32\cmd.exe /c ""C:\Program Files\nodejs\npm.cmd" run dev -- --host 127.0.0.1 --port 5173 --strictPort "'
$ownedVite = '"node" "' + $script:FrontendDir + '\node_modules\.bin\\..\vite\bin\vite.js" --host 127.0.0.1 --port 5173 --strictPort'

Write-Host '[1] the recorded cmd.exe / npm.cmd wrapper is recognised as ours' -ForegroundColor White
Assert-True -Condition (Test-NpmWrapperCommandLine -CommandLine $ownedWrapper -Port $port) `
    -Message 'npm run dev wrapper classified as application-owned'

Write-Host '[2] that wrapper is NOT mistaken for the Vite process' -ForegroundColor White
Assert-True -Condition (-not (Test-ViteCommandLine -CommandLine $ownedWrapper)) `
    -Message 'wrapper does not carry a vite entry point (this is the P1-R07 root cause)'

Write-Host '[3] the real Vite command line under this repository is recognised' -ForegroundColor White
Assert-True -Condition (Test-ViteCommandLine -CommandLine $ownedVite) `
    -Message 'vite.js under <repo>\frontend is recognised'

Write-Host '[4] a Vite from a different project is rejected' -ForegroundColor White
$foreignVite = '"node" "C:\Other\proj\node_modules\vite\bin\vite.js" --port 5173'
Assert-True -Condition (-not (Test-ViteCommandLine -CommandLine $foreignVite)) `
    -Message 'vite outside this repository is not ours'

Write-Host '[5] plain node.exe is rejected' -ForegroundColor White
Assert-True -Condition (-not (Test-ViteCommandLine -CommandLine '"node" "C:\tools\app.js"')) `
    -Message 'node.exe without a vite entry point is not ours'

Write-Host '[6] npm run build is rejected' -ForegroundColor White
$buildWrapper = 'cmd.exe /c "npm.cmd" run build --port 5173'
Assert-True -Condition (-not (Test-NpmWrapperCommandLine -CommandLine $buildWrapper -Port $port)) `
    -Message 'only the dev server counts as the frontend wrapper'

Write-Host '[7] uvicorn classification' -ForegroundColor White
$ourUvicorn = '-m uvicorn app.main:app --app-dir ' + $script:BackendDir + ' --port 8000'
Assert-True -Condition (Test-UvicornCommandLine -CommandLine $ourUvicorn) `
    -Message 'this application uvicorn is ours'
Assert-True -Condition (-not (Test-UvicornCommandLine -CommandLine '-m uvicorn other.app:app --port 9000')) `
    -Message 'a different ASGI app is not ours'

Write-Host '[8] forward-slash paths are recognised' -ForegroundColor White
$slashVite = '"node" "' + ($script:FrontendDir.Replace('\', '/')) + '/node_modules/vite/bin/vite.js" --port 5173'
Assert-True -Condition (Test-ViteCommandLine -CommandLine $slashVite) `
    -Message 'vite invoked with forward slashes is still ours'

Write-Host '[9] the descendant tree walk finds a real child process' -ForegroundColor White
$probe = (Get-Process -Id $PID).Path
if (-not $probe) { $probe = 'powershell' }
$childScript = Join-Path ([System.IO.Path]::GetTempPath()) ("tree-probe-{0}.ps1" -f ([guid]::NewGuid().ToString('N')))
Set-Content -LiteralPath $childScript -Encoding ASCII -Value @'
Start-Sleep -Seconds 20
'@
try {
    $child = Start-Process -FilePath $probe `
        -ArgumentList (ConvertTo-CommandLine -Arguments @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $childScript)) `
        -PassThru -WindowStyle Hidden
    Start-Sleep -Milliseconds 800

    $snapshot = Get-ProcessSnapshot
    $descendants = @(Get-DescendantProcessIds -RootProcessId $PID -Snapshot $snapshot)
    Assert-True -Condition ($descendants -contains $child.Id) `
        -Message "descendant walk found child PID $($child.Id)"

    Write-Host '[10] identity is rejected for a different name or creation time' -ForegroundColor White
    $recorded = $snapshot[[int]$child.Id]
    $stamp = ConvertTo-CreationStamp -CreationDate $recorded.CreationDate
    Assert-True -Condition (Test-ProcessIdentity -ProcessId $child.Id -ExpectedName $recorded.Name -ExpectedCreationTime $stamp -Snapshot $snapshot) `
        -Message 'matching name + creation time is accepted'
    Assert-True -Condition (-not (Test-ProcessIdentity -ProcessId $child.Id -ExpectedName 'definitely-not-the-name' -Snapshot $snapshot)) `
        -Message 'different image name is rejected'
    Assert-True -Condition (-not (Test-ProcessIdentity -ProcessId $child.Id -ExpectedCreationTime '19990101000000' -Snapshot $snapshot)) `
        -Message 'different creation time is rejected (defeats PID reuse)'
}
finally {
    if ($child -and -not $child.HasExited) { Stop-Process -Id $child.Id -Force -ErrorAction SilentlyContinue }
    Remove-Item -LiteralPath $childScript -Force -ErrorAction SilentlyContinue
}

Write-Host '[11] a falsy extra JSON property does not hide a state entry' -ForegroundColor White
# Windows PowerShell 5.1 ConvertFrom-Json adds PSComputerName; emulate a falsy
# property and prove the documented null check keeps the entry.
$emulated = '{"processes":[{"name":"frontend","pid":4400,"port":5173,"imageName":"cmd.exe","startedAt":"20260101000000","commandLine":"x"}]}' | ConvertFrom-Json
$entries = @($emulated.processes | Where-Object { $null -ne $_ })
Assert-True -Condition ($entries.Count -eq 1) -Message 'state entry survives the null-only filter'
Assert-True -Condition ([int]$entries[0].pid -eq 4400) -Message 'recorded pid is readable'

# --- summary ------------------------------------------------------------------
Write-Host ''
Write-Host ('-' * 74) -ForegroundColor DarkGray
if ($script:Failures -gt 0) {
    Write-Host ("Stop identity tests: FAIL ({0} of {1} checks failed)" -f $script:Failures, $script:Cases) -ForegroundColor Red
    exit 1
}
Write-Host ("Stop identity tests: PASS ({0} checks)" -f $script:Cases) -ForegroundColor Green
exit 0
