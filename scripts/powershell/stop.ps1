<#
.SYNOPSIS
    Stop only the application processes started by start.ps1.

.DESCRIPTION
    Identity-safe shutdown, designed around the real Windows process hierarchy
    that start.ps1 creates:

        powershell -> npm.cmd (cmd.exe) -> cmd.exe -> node.exe (vite)

    The recorded root is the npm.cmd/cmd.exe wrapper, whose command line does NOT
    contain "vite" or "node_modules" (P1-R07). Ownership is therefore decided
    from three independent, verified sources:

      1. the process recorded at startup (PID + image name + creation time), so a
         recycled PID is never mistaken for ours;
      2. the recorded wrapper command line (npm ... run dev --port 5173);
      3. the verified descendant tree, where a descendant is accepted only when
         its own command line is this repository's Vite entry point.

    Nothing is ever stopped because it merely owns port 8000 or 5173, and no
    process is stopped by image name. If ownership cannot be proven, the process
    is left alone and reported.

    Exit status
      0  every recorded process is gone AND ports 8000/5173 are free
      1  a recorded process could not be stopped and is still running
      2  processes were stopped but a port is still occupied (another owner)

    On any non-zero status the tracking files are KEPT so a retry has the same
    identity information; they are only removed after a fully successful stop.

    EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE

.PARAMETER Force
    Skip the graceful wait and terminate immediately after identity verification.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\powershell\stop.ps1
#>
[CmdletBinding()]
param(
    [switch]$Force
)

. "$PSScriptRoot\_common.ps1"

Write-Banner 'Stop: application-owned processes only'

$state = Read-StateFile
$results = New-Object System.Collections.Generic.List[object]

# --- helpers ------------------------------------------------------------------
function Stop-VerifiedProcess {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    Stop-Process -Id $ProcessId -ErrorAction SilentlyContinue

    if (-not $Force) {
        $deadline = (Get-Date).AddSeconds(10)
        while ((Get-Date) -lt $deadline) {
            if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return }
            Start-Sleep -Milliseconds 300
        }
    }

    if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
        # Identity was verified before this call, so a forced stop is limited to
        # a PID we proved is ours.
        Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
        $deadline = (Get-Date).AddSeconds(5)
        while ((Get-Date) -lt $deadline) {
            if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return }
            Start-Sleep -Milliseconds 200
        }
    }
}


if (-not $state) {
    Write-Warn "No run-state.json at $($script:StateFile) - nothing was started by start.ps1."
    Write-Host '  No process was stopped. This script never falls back to killing whatever owns a port.' -ForegroundColor DarkGray

    # Still tell the truth about the ports: if something holds them we cannot
    # prove it is ours, so this is not a success.
    $busyPorts = @(@($script:BackendPort, $script:FrontendPort) | Where-Object { Test-PortListening -Port $_ })
    Write-Host ''
    if ($busyPorts.Count -gt 0) {
        foreach ($port in $busyPorts) {
            Write-Warn "Port $port is listening, but there is no state file proving the owner is ours."
        }
        Write-Host 'Stop result: UNKNOWN - nothing was stopped (no state file)' -ForegroundColor Yellow
        Write-Host '  Inspect with: Get-NetTCPConnection -LocalPort 8000,5173 -State Listen | Select-Object OwningProcess' -ForegroundColor DarkGray
        exit 2
    }
    Write-Host 'Stop result: NOTHING TO DO' -ForegroundColor Yellow
    exit 0
}

# --- stop each recorded process ----------------------------------------------
$snapshot = Get-ProcessSnapshot

# Windows PowerShell 5.1's ConvertFrom-Json adds a PSComputerName property to
# every object, and that property is falsy. A bare `if (-not $entry)` would
# therefore skip EVERY entry and report a clean stop without doing anything.
# The null check is explicit for that reason.
$entries = @($state.processes | Where-Object { $null -ne $_ })
if ($entries.Count -eq 0) {
    Write-Warn "run-state.json contains no process entries; nothing can be verified. Not stopping anything."
    Write-Host 'Stop result: FAILED - state file present but empty' -ForegroundColor Red
    exit 1
}

foreach ($entry in $entries) {
    $entryPid = 0
    if (-not [int]::TryParse([string]$entry.pid, [ref]$entryPid)) {
        Write-Warn "Skipping a state entry without a usable pid: $($entry.pid)"
        continue
    }

    $processId = $entryPid
    $name = [string]$entry.name
    $port = if ($entry.port) { [int]$entry.port } elseif ($name -eq 'backend') { $script:BackendPort } else { $script:FrontendPort }
    $recordedName = [string]$entry.imageName
    $recordedStart = [string]$entry.startedAt
    $recordedCommand = [string]$entry.commandLine

    $record = [pscustomobject]@{
        name        = $name
        pid         = $processId
        port        = $port
        commandLine = $recordedCommand
        imageName   = $recordedName
        startedAt   = $recordedStart
    }

    Write-Step "Checking $name (recorded PID $processId)"

    # --- 1. is the recorded PID still OUR process? ---------------------------
    if ($snapshot.ContainsKey($processId)) {
        $live = $snapshot[$processId]
        $sameName = (-not $recordedName) -or ($live.Name -eq $recordedName)
        $sameStart = (-not $recordedStart) -or ((ConvertTo-CreationStamp -CreationDate $live.CreationDate) -eq $recordedStart)

        if (-not ($sameName -and $sameStart)) {
            Write-Warn "  PID $processId now belongs to a different process ($($live.Name)). It was NOT ours; leaving it alone."
            $results.Add([pscustomobject]@{ outcome = 'not-ours'; record = $record })
            continue
        }
    }

    $root = if ($snapshot.ContainsKey($processId)) { $snapshot[$processId] } else { $null }
    $rootCommand = if ($root) { $root.CommandLine } else { $recordedCommand }

    # --- 2. work out which processes in this tree are ours -------------------
    $targets = New-Object System.Collections.Generic.List[int]

    if ($name -eq 'backend') {
        # uvicorn is launched directly by start.ps1: its own command line is
        # decisive, and its children die with it.
        if ($root -and (Test-UvicornCommandLine -CommandLine $rootCommand)) {
            $targets.Add($processId)
        }
        elseif (-not $root) {
            Write-Ok "  backend (PID $processId) is already gone"
            $results.Add([pscustomobject]@{ outcome = 'stopped'; record = $record })
            continue
        }
        else {
            Write-Warn "  PID $processId does not look like this application's uvicorn. Leaving it alone."
            $results.Add([pscustomobject]@{ outcome = 'not-ours'; record = $record })
            continue
        }
    }
    else {
        # Frontend: npm.cmd -> cmd.exe -> node.exe -> vite.
        # The wrapper is accepted from its recorded identity plus its own
        # npm-run-dev command line; the Vite process is accepted only from the
        # verified descendant tree AND its own Vite command line.
        $wrapperAccepted = $false
        if ($root) {
            if (Test-NpmWrapperCommandLine -CommandLine $rootCommand -Port $port) {
                $wrapperAccepted = $true
            }
            elseif (Test-ViteCommandLine -CommandLine $rootCommand) {
                $wrapperAccepted = $true
            }
            elseif ($recordedCommand -and (Test-NpmWrapperCommandLine -CommandLine $recordedCommand -Port $port)) {
                Write-Host "  recorded wrapper command line matches npm run dev on port $port" -ForegroundColor DarkGray
                $wrapperAccepted = $true
            }
        }

        # Descendants are only considered when the recorded PID is genuinely
        # ours (or already gone), never for an unrelated process on the port.
        if (-not $root -or $wrapperAccepted) {
            $freshSnapshot = Get-ProcessSnapshot
            $descendants = @(Get-DescendantProcessIds -RootProcessId $processId -Snapshot $freshSnapshot)
            # Children first: the Vite process must be gone before the wrapper
            # that parents it, otherwise it can be re-parented mid-shutdown.
            foreach ($childId in $descendants) {
                if (-not $freshSnapshot.ContainsKey($childId)) { continue }
                $child = $freshSnapshot[$childId]
                if (Test-ViteCommandLine -CommandLine $child.CommandLine) {
                    $targets.Add($childId)
                }
            }

            # Orphan case: the wrapper exited but its Vite child survived and was
            # re-parented to a dead PID. The child is identified ONLY by this
            # repository's Vite entry point - never by port alone.
            if (-not $root) {
                foreach ($candidate in $freshSnapshot.Values) {
                    if (Test-ViteCommandLine -CommandLine $candidate.CommandLine) {
                        $parentAlive = $freshSnapshot.ContainsKey($candidate.ParentProcessId)
                        if (-not $parentAlive -and -not $targets.Contains($candidate.ProcessId)) {
                            Write-Host "  adopted orphaned Vite process PID $($candidate.ProcessId) (parent $($candidate.ParentProcessId) is gone)" -ForegroundColor DarkGray
                            $targets.Add($candidate.ProcessId)
                        }
                    }
                }
            }
        }

        # The wrapper itself goes last, after every verified child.
        if ($root -and $wrapperAccepted -and -not $targets.Contains($processId)) {
            $targets.Add($processId)
        }

        if (-not $root -and $targets.Count -eq 0) {
            Write-Ok "  frontend (PID $processId) is already gone"
            $results.Add([pscustomobject]@{ outcome = 'stopped'; record = $record })
            continue
        }
        if (-not $wrapperAccepted -and $targets.Count -eq 0) {
            Write-Warn "  PID $processId is not this application's npm/vite process. Leaving it alone."
            $results.Add([pscustomobject]@{ outcome = 'not-ours'; record = $record })
            continue
        }
    }

    # --- 3. stop the verified targets, children first ------------------------
    if ($targets.Count -eq 0) {
        Write-Warn "  nothing to stop for $name"
        $results.Add([pscustomobject]@{ outcome = 'not-ours'; record = $record })
        continue
    }

    Write-Host "      stopping PIDs: $($targets -join ', ')" -ForegroundColor DarkGray
    foreach ($targetId in $targets) {
        Stop-VerifiedProcess -ProcessId $targetId
    }

    Start-Sleep -Milliseconds 400
    $stillRunning = @($targets | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue })
    if ($stillRunning.Count -gt 0) {
        Write-Fail "  $name could not be stopped (still running: $($stillRunning -join ', '))"
        $results.Add([pscustomobject]@{ outcome = 'failed'; record = $record })
    }
    else {
        Write-Ok "$name stopped (PIDs: $($targets -join ', '))"
        $results.Add([pscustomobject]@{ outcome = 'stopped'; record = $record })
    }
}

# --- stale PID files without a state file ------------------------------------
# Only acted on when the recorded PID still has OUR identity and command line.
foreach ($pidFile in @($script:FrontendPidFile, $script:BackendPidFile)) {
    if (-not (Test-Path -LiteralPath $pidFile)) { continue }
    $recorded = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if (-not $recorded) { continue }
    $pidValue = 0
    if (-not [int]::TryParse($recorded, [ref]$pidValue)) { continue }

    $freshSnapshot = Get-ProcessSnapshot
    if (-not $freshSnapshot.ContainsKey($pidValue)) { continue }

    $candidate = $freshSnapshot[$pidValue]
    $isOurVite = Test-ViteCommandLine -CommandLine $candidate.CommandLine
    $isOurNpm = Test-NpmWrapperCommandLine -CommandLine $candidate.CommandLine -Port $script:FrontendPort
    if ($isOurVite -or $isOurNpm) {
        Write-Step "Stopping leftover frontend process (PID $pidValue from $([System.IO.Path]::GetFileName($pidFile)))"
        $toStop = @($pidValue) + @(Get-DescendantProcessIds -RootProcessId $pidValue -Snapshot $freshSnapshot |
                Where-Object { Test-ViteCommandLine -CommandLine $freshSnapshot[$_].CommandLine })
        foreach ($targetId in $toStop) { Stop-VerifiedProcess -ProcessId $targetId }
    }
}

# --- outcome ------------------------------------------------------------------
# The verdict is decided BEFORE any tracking file is touched (P1-R08): an
# incomplete result must never delete the provenance needed to diagnose it.
$failed = @($results | Where-Object { $_.outcome -eq 'failed' })
$notOurs = @($results | Where-Object { $_.outcome -eq 'not-ours' })
$stopped = @($results | Where-Object { $_.outcome -eq 'stopped' })

Write-Host ''
$busyPorts = @(@($script:BackendPort, $script:FrontendPort) | Where-Object { Test-PortListening -Port $_ })
foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
    if ($busyPorts -contains $port) {
        Write-Warn "Port $port is still listening"
    }
    else {
        Write-Ok "Port $port is free"
    }
}

$verdict = Get-ShutdownVerdict -FailedCount $failed.Count -BlockedCount $notOurs.Count -BusyPorts $busyPorts

# Survivors to keep: failed stops, and recorded PIDs that are still alive but
# could not be verified (a not-ours entry that is already gone needs no retry).
$survivorRecords = @()
foreach ($entry in @($failed) + @($notOurs)) {
    $recordedPid = [int]$entry.record.pid
    if ($entry.outcome -eq 'failed' -or (Get-Process -Id $recordedPid -ErrorAction SilentlyContinue)) {
        $survivorRecords += $entry.record
    }
}

$incompleteReason = 'clean'
if ($failed.Count -gt 0) { $incompleteReason = 'process-stop-failed' }
elseif ($notOurs.Count -gt 0) { $incompleteReason = 'process-unverified' }
elseif (-not $verdict.Clean) { $incompleteReason = 'port-still-occupied' }

# Tracking is rewritten or kept according to the verdict; only a clean result
# removes it.
Save-StopState -Remaining $survivorRecords -Clean $verdict.Clean -Reason $incompleteReason

Write-Host ''
switch ($verdict.Status) {
    'FAILED' {
        Write-Host "Stop result: FAILED - $($failed.Count) application process(es) could not be stopped" -ForegroundColor Red
        Write-Host '  Tracking files were KEPT so you can retry: .\scripts\powershell\stop.ps1 -Force' -ForegroundColor DarkGray
        exit 1
    }
    'BLOCKED' {
        Write-Host "Stop result: BLOCKED - $($notOurs.Count) recorded process(es) are still running but could not be verified as ours" -ForegroundColor Red
        Write-Host '  Nothing was killed. Tracking files were KEPT.' -ForegroundColor DarkGray
        Write-Host '  Inspect each one, then decide manually:' -ForegroundColor DarkGray
        Write-Host '    Get-CimInstance Win32_Process -Filter "ProcessId = <pid>" | Select-Object Name, CommandLine' -ForegroundColor DarkGray
        exit 1
    }
    'INCOMPLETE' {
        Write-Host "Stop result: INCOMPLETE - port(s) $($busyPorts -join ', ') still in use" -ForegroundColor Yellow
        Write-Host '  Tracking files were KEPT with the original metadata (partial = true).' -ForegroundColor DarkGray
        Write-Host '  The process holding a port could not be traced to this application.' -ForegroundColor DarkGray
        Write-Host '  Inspect it with: Get-NetTCPConnection -LocalPort 8000,5173 -State Listen | Select-Object OwningProcess' -ForegroundColor DarkGray
        Write-Host '  Then: Get-CimInstance Win32_Process -Filter "ProcessId = <pid>" | Select-Object Name, CommandLine' -ForegroundColor DarkGray
        exit 2
    }
    default {
        Write-Host "Stop result: PASS - $($stopped.Count) stopped, ports 8000 and 5173 are free" -ForegroundColor Green
        Write-Host 'Runtime artifacts (logs, database) are kept for inspection; delete data\runtime manually for a clean slate.' -ForegroundColor DarkGray
        exit 0
    }
}
