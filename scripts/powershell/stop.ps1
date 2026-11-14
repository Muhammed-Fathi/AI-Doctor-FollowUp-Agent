<#
.SYNOPSIS
    Stop only the application processes started by start.ps1.

.DESCRIPTION
    Identity-safe shutdown:

      1. Reads `data/runtime/run-state.json` (written by start.ps1).
      2. For each recorded PID, re-reads the live command line.
      3. Stops the process ONLY when the command line still belongs to this
         repository's application (uvicorn with this app-dir / a vite dev server
         in this frontend directory).
      4. Refuses to fall back to "kill anything on port 8000". If no state file
         exists, it reports the situation and does nothing.

    Uses SIGTERM-equivalent (Stop-Process without -Force) first, waits, and
    falls back to -Force only for a PID it has already verified.

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
$stopped = 0
$skipped = 0

function Test-OwnedProcess {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId,
        [Parameter(Mandatory = $true)][string]$Name
    )

    $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $process) {
        return $false
    }

    $commandLine = Get-ProcessCommandLine -ProcessId $ProcessId
    if (-not $commandLine) {
        # Cannot verify identity -> do not touch it.
        Write-Warn "PID $ProcessId ($Name): command line unavailable to CIM. Not stopping it."
        return $false
    }

    $isOwned = $false

    if ($Name -eq 'backend') {
        # uvicorn is launched directly by this script, so its command line always
        # carries both the repository path and the app target.
        $rootEscaped = [Regex]::Escape($script:RepoRoot)
        $belongsToRepo = $commandLine -match $rootEscaped
        $looksLikeBackend = $commandLine -match 'uvicorn' -and $commandLine -match 'app\.main:app'
        $isOwned = $belongsToRepo -and $looksLikeBackend
    }
    elseif ($Name -eq 'frontend') {
        # npm.cmd -> cmd.exe -> node.exe. The intermediate cmd.exe wrapper often
        # carries only the npm invocation, without the repository path (P1-R05),
        # so identity is established by the Vite signature of this project plus
        # ANY of: the repository path, the dev-script invocation, or the
        # frontend port flag that start.ps1 always passes.
        $looksLikeFrontend = $commandLine -match 'vite' -or $commandLine -match 'node_modules'
        $rootEscaped = [Regex]::Escape($script:RepoRoot)
        $referencesRepo = ($commandLine -match $rootEscaped) -or
            ($commandLine -match 'run\s+dev') -or
            ($commandLine -match "--port\s+$($script:FrontendPort)\b") -or
            ($commandLine -match 'strictPort')
        $isOwned = $looksLikeFrontend -and $referencesRepo
    }

    if (-not $isOwned) {
        Write-Warn "PID $ProcessId ($Name): command line does not match this repository. Not stopping it."
    }
    return $isOwned
}

# Returns the process tree below $RootProcessId (npm.cmd -> cmd.exe -> node.exe).
# Only used after the root process was verified as application-owned.
function Get-DescendantProcessIds {
    param([Parameter(Mandatory = $true)][int]$RootProcessId)

    $all = Get-CimInstance -ClassName Win32_Process -ErrorAction SilentlyContinue
    if (-not $all) { return @() }

    $children = @{}
    foreach ($process in $all) {
        $parent = [int]$process.ParentProcessId
        if (-not $children.ContainsKey($parent)) {
            $children[$parent] = New-Object System.Collections.Generic.List[int]
        }
        $children[$parent].Add([int]$process.ProcessId)
    }

    $result = New-Object System.Collections.Generic.List[int]
    $queue = New-Object System.Collections.Generic.Queue[int]
    $queue.Enqueue($RootProcessId)
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        if ($children.ContainsKey($current)) {
            foreach ($child in $children[$current]) {
                if (-not $result.Contains($child)) {
                    $result.Add($child)
                    $queue.Enqueue($child)
                }
            }
        }
    }
    return $result
}

if (-not $state) {
    Write-Warn "No run-state.json at $($script:StateFile) - nothing was started by start.ps1."
    Write-Host '  No process was stopped. This script never falls back to killing whatever owns a port.' -ForegroundColor DarkGray
    Write-Host ''
    Write-Host 'Stop result: NOTHING TO DO' -ForegroundColor Yellow
    exit 0
}

foreach ($entry in @($state.processes)) {
    if (-not $entry -or -not $entry.pid) { continue }
    $processId = [int]$entry.pid
    $name = [string]$entry.name

    if (-not (Test-OwnedProcess -ProcessId $processId -Name $name)) {
        $skipped++
        continue
    }

    Write-Step "Stopping $name (PID $processId)"
    try {
        # npm.cmd spawns cmd.exe -> node.exe; the children must go too, or the
        # Vite dev server keeps port 5173 open. Children are collected only
        # after the root PID was verified as application-owned above.
        $descendants = @(Get-DescendantProcessIds -RootProcessId $processId)
        if ($descendants.Count -gt 0) {
            Write-Host "      child processes: $($descendants -join ', ')" -ForegroundColor DarkGray
        }

        Stop-Process -Id $processId -ErrorAction Stop

        if (-not $Force) {
            $deadline = (Get-Date).AddSeconds(10)
            while ((Get-Date) -lt $deadline) {
                if (-not (Get-Process -Id $processId -ErrorAction SilentlyContinue)) { break }
                Start-Sleep -Milliseconds 300
            }
        }

        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) {
            # Identity was verified above, so a forced stop is limited to our own PID.
            Stop-Process -Id $processId -Force -ErrorAction Stop
        }

        foreach ($childId in $descendants) {
            if (Get-Process -Id $childId -ErrorAction SilentlyContinue) {
                Stop-Process -Id $childId -Force -ErrorAction SilentlyContinue
            }
        }

        Write-Ok "$name stopped"
        $stopped++
    }
    catch {
        Write-Fail "Could not stop $name (PID $processId): $($_.Exception.Message)"
        $skipped++
    }
}

# A frontend PID file may survive a partial start. It is only acted on when the
# recorded PID still exists AND its command line is this repository's Vite server.
$frontendPidFile = $script:FrontendPidFile
if (Test-Path -LiteralPath $frontendPidFile) {
    $recorded = (Get-Content -LiteralPath $frontendPidFile -Raw).Trim()
    if ($recorded -and (Get-Process -Id $recorded -ErrorAction SilentlyContinue)) {
        if (Test-OwnedProcess -ProcessId ([int]$recorded) -Name 'frontend') {
            Write-Step "Stopping leftover frontend wrapper (PID $recorded)"
            foreach ($childId in @(Get-DescendantProcessIds -RootProcessId ([int]$recorded))) {
                Stop-Process -Id $childId -Force -ErrorAction SilentlyContinue
            }
            Stop-Process -Id ([int]$recorded) -Force -ErrorAction SilentlyContinue
            $stopped++
            Write-Ok 'leftover frontend wrapper stopped'
        }
    }
}

Remove-Item -LiteralPath $script:StateFile -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $script:BackendPidFile -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $script:FrontendPidFile -Force -ErrorAction SilentlyContinue

# --- report -------------------------------------------------------------------
Write-Host ''
foreach ($port in @($script:BackendPort, $script:FrontendPort)) {
    if (Test-PortListening -Port $port) {
        Write-Warn "Port $port is still listening - it belongs to a process this script does not own."
    }
    else {
        Write-Ok "Port $port is free"
    }
}

Write-Host ''
Write-Host "Stop result: $stopped stopped, $skipped not stopped" -ForegroundColor Green
Write-Host 'Runtime artifacts (logs, database) are kept for inspection; delete data\runtime manually for a clean slate.' -ForegroundColor DarkGray
exit 0
