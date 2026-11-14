<#
.SYNOPSIS
    Start the local demo (FastAPI backend, and optionally the Vite frontend).

.DESCRIPTION
    Starts ONLY processes this project owns, records their PIDs in
    `data/runtime/`, and writes `run-state.json` so `stop.ps1` can verify
    process identity before stopping anything.

    Safety rules implemented here:
      * refuses to start when the same application process is already running
        (it reports the existing instance instead of duplicating it);
      * never kills an unrelated process occupying a port - it reports the
        conflict and stops;
      * the backend binds 127.0.0.1 only;
      * no window is hidden and no execution policy is changed.

    EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE

.PARAMETER BackendOnly
    Start only the FastAPI backend (no Vite dev server).

.PARAMETER NoBrowser
    Do not open the default browser.

.PARAMETER TimeoutSeconds
    How long to wait for `/health` to answer before declaring failure.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\start.ps1
#>
[CmdletBinding()]
param(
    [switch]$BackendOnly,
    [switch]$NoBrowser,
    [int]$TimeoutSeconds = 60
)

. "$PSScriptRoot\_common.ps1"

Write-Banner 'Start: local demo'

$venvPython = Get-VenvPython
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Fail "No virtual environment at $(Get-VenvDir). Run setup.ps1 first."
    exit 1
}

$envFile = Join-Path $script:RepoRoot '.env'
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Warn '.env is missing; defaults from the application will be used (setup.ps1 creates it).'
}

Ensure-RuntimeDir | Out-Null

# --- already running? ---------------------------------------------------------
$previousState = Read-StateFile
if ($previousState) {
    $stillRunning = $false
    foreach ($entry in @($previousState.processes)) {
        if ($entry -and $entry.pid -and (Get-Process -Id $entry.pid -ErrorAction SilentlyContinue)) {
            $stillRunning = $true
        }
    }
    if ($stillRunning) {
        Write-Warn 'An application instance is already running. Use stop.ps1 first if you want a restart.'
        Write-Host "  state file: $($script:StateFile)" -ForegroundColor DarkGray
        exit 1
    }
    Write-Warn 'A stale run-state.json was found (no matching processes); it will be replaced.'
}

# --- port conflicts -----------------------------------------------------------
$ports = @($script:BackendPort)
if (-not $BackendOnly) { $ports += $script:FrontendPort }
foreach ($port in $ports) {
    if (Test-PortListening -Port $port) {
        Write-Fail "Port $port is already in use by another process. Nothing was started."
        Write-Host "  Inspect it with: Get-NetTCPConnection -LocalPort $port -State Listen | Select-Object OwningProcess" -ForegroundColor DarkGray
        Write-Host '  This script never terminates a process it did not start.' -ForegroundColor DarkGray
        exit 1
    }
}

$started = New-Object System.Collections.Generic.List[object]

# Captures the identity of a process we just launched, so stop.ps1 can later
# prove the PID is still ours (PID + image name + creation time). Without the
# creation time a recycled PID could be stopped by mistake (P1-R07).
function New-StartedRecord {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][int]$ProcessId
    )

    $snapshot = Get-ProcessSnapshot
    $imageName = ''
    $creation = ''
    $commandLine = ''
    if ($snapshot.ContainsKey($ProcessId)) {
        $live = $snapshot[$ProcessId]
        $imageName = $live.Name
        $creation = ConvertTo-CreationStamp -CreationDate $live.CreationDate
        $commandLine = $live.CommandLine
    }

    return [pscustomobject]@{
        Name        = $Name
        pid         = $ProcessId
        imageName   = $imageName
        startedAt   = $creation
        commandLine = $commandLine
    }
}

# Rolls back exactly what this run started. npm.cmd -> cmd.exe -> node.exe means
# stopping only the recorded wrapper leaks the Vite server, so the verified
# child tree is stopped too (same hierarchy as stop.ps1, P1-R07).
function Stop-StartedProcesses {
    param([System.Collections.Generic.List[object]]$List)

    foreach ($item in $List) {
        $snapshot = Get-ProcessSnapshot

        # Only touch the recorded PID when it still is the process we started.
        if ($snapshot.ContainsKey($item.pid)) {
            $live = $snapshot[$item.pid]
            $sameName = (-not $item.imageName) -or ($live.Name -eq $item.imageName)
            $sameStart = (-not $item.startedAt) -or ((ConvertTo-CreationStamp -CreationDate $live.CreationDate) -eq $item.startedAt)
            if (-not ($sameName -and $sameStart)) {
                Write-Warn "Rollback skipped $($item.Name): PID $($item.pid) now belongs to another process."
                continue
            }
        }

        $targets = New-Object System.Collections.Generic.List[int]
        $targets.Add($item.pid)

        # Children first, then the wrapper.
        foreach ($childId in @(Get-DescendantProcessIds -RootProcessId $item.pid -Snapshot $snapshot)) {
            if ($snapshot.ContainsKey($childId)) {
                $targets.Add($childId)
            }
        }

        $stoppedAny = $false
        foreach ($targetId in $targets) {
            if (Get-Process -Id $targetId -ErrorAction SilentlyContinue) {
                Stop-Process -Id $targetId -Force -ErrorAction SilentlyContinue
                $stoppedAny = $true
            }
        }
        if ($stoppedAny) {
            Write-Warn "Rolled back $($item.Name) (PID $($item.pid), $($targets.Count) process(es) in its tree)."
        }
    }
}

try {
    # --- backend --------------------------------------------------------------
    Write-Step 'Starting FastAPI backend on 127.0.0.1:8000'
    $backendLog = Join-Path $script:RuntimeDir 'backend.out.log'
    $backendErrLog = Join-Path $script:RuntimeDir 'backend.err.log'

    $backendArgs = @(
        '-m', 'uvicorn', 'app.main:app',
        '--host', '127.0.0.1',
        '--port', "$($script:BackendPort)",
        '--app-dir', $script:BackendDir,
        '--log-level', 'info'
    )

    # -ArgumentList is joined into one command line string by Start-Process, so
    # every element is quoted here; otherwise a repository path containing a
    # space (e.g. `E:\My Projects\...`) breaks --app-dir (P1-R03).
    $backendProcess = Start-Process -FilePath $venvPython `
        -ArgumentList (ConvertTo-CommandLine -Arguments $backendArgs) `
        -WorkingDirectory $script:RepoRoot `
        -RedirectStandardOutput $backendLog `
        -RedirectStandardError $backendErrLog `
        -PassThru `
        -WindowStyle Hidden

    $started.Add((New-StartedRecord -Name 'backend' -ProcessId $backendProcess.Id))
    Set-Content -LiteralPath $script:BackendPidFile -Value $backendProcess.Id -Encoding ASCII
    Write-Ok "backend started (PID $($backendProcess.Id))"

    $healthUrl = "http://127.0.0.1:$($script:BackendPort)/health"
    if (-not (Wait-HttpOk -Url $healthUrl -TimeoutSeconds $TimeoutSeconds)) {
        throw "Backend did not answer $healthUrl within $TimeoutSeconds s. See $backendLog and $backendErrLog."
    }
    Write-Ok "GET $healthUrl -> 200"

    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
    Write-Host ("      status={0} db={1} ollama={2} tesseract={3}" -f $health.status, $health.db, $health.ollama, $health.tesseract) -ForegroundColor DarkGray

    # --- frontend -------------------------------------------------------------
    if (-not $BackendOnly) {
        $nodeModules = Join-Path $script:FrontendDir 'node_modules'
        if (-not (Test-Path -LiteralPath $nodeModules)) {
            throw "frontend/node_modules is missing. Run setup.ps1 first."
        }

        Write-Step "Starting Vite dev server on 127.0.0.1:$($script:FrontendPort)"
        $frontendLog = Join-Path $script:RuntimeDir 'frontend.out.log'
        $frontendErrLog = Join-Path $script:RuntimeDir 'frontend.err.log'

        # npm.cmd, because npm.ps1 may be blocked by the execution policy.
        $frontendArgs = @(
            'run', 'dev', '--',
            '--host', '127.0.0.1',
            '--port', "$($script:FrontendPort)",
            '--strictPort'
        )

        $frontendProcess = Start-Process -FilePath 'npm.cmd' `
            -ArgumentList (ConvertTo-CommandLine -Arguments $frontendArgs) `
            -WorkingDirectory $script:FrontendDir `
            -RedirectStandardOutput $frontendLog `
            -RedirectStandardError $frontendErrLog `
            -PassThru `
            -WindowStyle Hidden

        $started.Add((New-StartedRecord -Name 'frontend' -ProcessId $frontendProcess.Id))
        Set-Content -LiteralPath $script:FrontendPidFile -Value $frontendProcess.Id -Encoding ASCII
        Write-Ok "frontend started (PID $($frontendProcess.Id))"

        $frontendUrl = "http://127.0.0.1:$($script:FrontendPort)/"
        if (-not (Wait-HttpOk -Url $frontendUrl -TimeoutSeconds $TimeoutSeconds)) {
            throw "Frontend did not answer $frontendUrl within $TimeoutSeconds s. See $frontendLog and $frontendErrLog."
        }
        Write-Ok "GET $frontendUrl -> 200"
    }

    # --- state file -----------------------------------------------------------
    $state = [pscustomobject]@{
        schemaVersion = 2
        startedAt     = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
        repoRoot      = $script:RepoRoot
        venvDir       = (Get-VenvDir)
        processes     = @($started | ForEach-Object {
                [pscustomobject]@{
                    name        = $_.Name
                    pid         = $_.pid
                    port        = if ($_.Name -eq 'backend') { $script:BackendPort } else { $script:FrontendPort }
                    imageName   = $_.imageName
                    startedAt   = $_.startedAt
                    commandLine = $_.commandLine
                }
            })
    }
    $state | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $script:StateFile -Encoding UTF8

    Write-Host ''
    Write-Host 'Start result: PASS' -ForegroundColor Green
    Write-Host ''
    Write-Host "  API      : http://127.0.0.1:$($script:BackendPort)/health"
    Write-Host "  Version  : http://127.0.0.1:$($script:BackendPort)/version"
    Write-Host "  API docs : http://127.0.0.1:$($script:BackendPort)/docs"
    if (-not $BackendOnly) {
        Write-Host "  Frontend : http://127.0.0.1:$($script:FrontendPort)/"
    }
    Write-Host "  Logs     : $($script:RuntimeDir)"
    Write-Host "  Stop     : powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\stop.ps1"
    Write-Host ''
    Write-Host 'Logs are application-owned and gitignored. Nothing is exposed beyond 127.0.0.1.' -ForegroundColor DarkGray

    if (-not $NoBrowser -and -not $BackendOnly) {
        try {
            Start-Process "http://127.0.0.1:$($script:FrontendPort)/" | Out-Null
        }
        catch {
            Write-Warn 'Could not open the default browser; open the URL manually.'
        }
    }

    exit 0
}
catch {
    Write-Fail $_.Exception.Message
    Write-Step 'Rolling back started processes'
    Stop-StartedProcesses -List $started

    # Verify the rollback instead of asserting it (P1-R08): a child that survived
    # rollback must not be reported as "nothing is left running", and the
    # tracking files must stay so the leftover can be found and stopped.
    $leftovers = @()
    foreach ($item in $started) {
        if (Get-Process -Id $item.pid -ErrorAction SilentlyContinue) {
            $leftovers += $item
            continue
        }
        $snapshot = Get-ProcessSnapshot
        foreach ($childId in @(Get-DescendantProcessIds -RootProcessId $item.pid -Snapshot $snapshot)) {
            if ($snapshot.ContainsKey($childId)) {
                $leftovers += [pscustomobject]@{ Name = "$($item.Name) child"; pid = $childId }
            }
        }
    }

    if ($leftovers.Count -eq 0) {
        Remove-Item -LiteralPath $script:StateFile -Force -ErrorAction SilentlyContinue
        foreach ($pidFile in @($script:BackendPidFile, $script:FrontendPidFile)) {
            Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
        }
        Write-Fail 'Start failed; nothing is left running.'
        exit 1
    }

    # Keep the state so the survivor is traceable, and describe it honestly.
    Write-Fail "Start failed and rollback was INCOMPLETE - $($leftovers.Count) process(es) survived:"
    foreach ($item in $leftovers) {
        Write-Host "      $($item.Name) PID $($item.pid)" -ForegroundColor Red
    }
    Write-Host "  Tracking kept in $($script:RuntimeDir); run stop.ps1 to retry the shutdown." -ForegroundColor Yellow
    exit 1
}
