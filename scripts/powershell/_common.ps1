# =============================================================================
# scripts/powershell/_common.ps1
# Shared helpers for the AI Doctor Follow-Up Windows scripts.
# EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE
#
# Dot-source this file from a script; it is not meant to be run directly.
#   . "$PSScriptRoot\_common.ps1"
#
# Design rules (AGENTS.md, P1 task):
#   * every path is resolved relative to the repository root, never to $PWD;
#   * paths with spaces are always quoted;
#   * failures propagate (external commands are checked with $LASTEXITCODE);
#   * nothing here kills processes by image name or terminates broadly.
# =============================================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- repository layout --------------------------------------------------------
# $PSScriptRoot = <repo>\scripts\powershell  ->  repository root is two levels up.
$script:RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$script:ScriptsDir = Join-Path $script:RepoRoot 'scripts\powershell'
$script:RuntimeDir = Join-Path $script:RepoRoot 'data\runtime'
$script:BackendDir = Join-Path $script:RepoRoot 'backend'
$script:FrontendDir = Join-Path $script:RepoRoot 'frontend'
$script:AlembicIni = Join-Path $script:BackendDir 'migrations\alembic.ini'

# Virtual environment location. Defaults to <repo>\.venv, but can be moved to
# another drive (the owner keeps dependencies on E:) with:
#   $env:APP_VENV_DIR = 'E:\AI-Doctor-FollowUp-Agent\.venv'
function Get-VenvDir {
    if ($env:APP_VENV_DIR) {
        return $env:APP_VENV_DIR
    }
    return (Join-Path $script:RepoRoot '.venv')
}

function Get-VenvPython {
    return (Join-Path (Get-VenvDir) 'Scripts\python.exe')
}

# --- required interpreter / runtime versions ---------------------------------
$script:RequiredPython = '3.12'
$script:MinNodeMajor = 20
$script:MinNodeMinorForTwenty = 19
$script:MinNodeMajorForTwentyTwo = 22
$script:MinNodeMinorForTwentyTwo = 12

# Ports used by the local demo (loopback only).
$script:BackendPort = 8000
$script:FrontendPort = 5173
$script:FrontendPreviewPort = 4173

# PID/state files written by start.ps1 and read by stop.ps1.
$script:BackendPidFile = Join-Path $script:RuntimeDir 'backend.pid'
$script:FrontendPidFile = Join-Path $script:RuntimeDir 'frontend.pid'
$script:StateFile = Join-Path $script:RuntimeDir 'run-state.json'

# --- output helpers -----------------------------------------------------------
function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "  OK  $Message" -ForegroundColor Green
}

function Write-Warn {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "  !!  $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host "  XX  $Message" -ForegroundColor Red
}

function Write-Banner {
    param([Parameter(Mandatory = $true)][string]$Title)
    $line = '=' * 74
    Write-Host ''
    Write-Host $line -ForegroundColor DarkGray
    Write-Host "  $Title" -ForegroundColor White
    Write-Host '  EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE' -ForegroundColor Yellow
    Write-Host $line -ForegroundColor DarkGray
    Write-Host ''
}

# --- external command execution ----------------------------------------------
# Runs a native command, streams its output to the console, and returns ONLY the
# numeric exit code.
#
# IMPORTANT (P1-R06): a native command's stdout is written into the caller's
# *success pipeline*. Without the explicit `Out-Host` below, output such as
# "All checks passed!" is emitted next to the exit code, so a caller doing
# `$code = Invoke-Native ...` receives an array whose comparison with 0 is false
# even when the command succeeded. `Out-Host` writes the same text to the same
# console (visible, unaltered) while keeping it out of the pipeline.
#
# stderr is deliberately NOT redirected: it already goes to the console, and
# merging it (`2>&1`) under $ErrorActionPreference='Stop' would turn benign
# native stderr writes into terminating errors on Windows PowerShell 5.1.
function Invoke-Native {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = $script:RepoRoot,
        [switch]$AllowFailure
    )

    # Never let a stale value from an earlier command leak into the result.
    $code = 0

    Push-Location -LiteralPath $WorkingDirectory
    try {
        & $FilePath @Arguments | Out-Host
        if ($null -ne $LASTEXITCODE) {
            $code = [int]$LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }

    if ($code -ne 0 -and -not $AllowFailure) {
        throw "Command failed (exit $code): $FilePath $($Arguments -join ' ')"
    }
    return $code
}

# Captures stdout of a native command. Returns an object with the numeric exit
# code and the trimmed output; never a fake value.
#
# `$LASTEXITCODE` is read into a variable and the captured pipeline is flattened
# with `-join` before anything else runs, so a value written by the command that
# happens to look numeric can never be mistaken for the exit code.
function Get-NativeOutput {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$WorkingDirectory = $script:RepoRoot
    )

    $code = 0
    $output = @()

    Push-Location -LiteralPath $WorkingDirectory
    try {
        $output = @(& $FilePath @Arguments 2>&1)
        if ($null -ne $LASTEXITCODE) {
            $code = [int]$LASTEXITCODE
        }
    }
    finally {
        Pop-Location
    }

    return [pscustomobject]@{ ExitCode = $code; Output = (@($output) -join "`n").Trim() }
}

# Quotes a single argument for the Windows command line.
#
# `Start-Process -ArgumentList` joins the array with spaces and hands the result
# to CreateProcess as ONE string; an element such as
# `--app-dir E:\My Projects\repo\backend` therefore splits on the space and the
# child receives a truncated path (P1-R03). Every element is quoted explicitly.
#
# Only arguments that contain whitespace, quotes or are empty are quoted, so
# ordinary flags stay readable in logs and error messages.
function ConvertTo-QuotedArgument {
    param([Parameter(Mandatory = $true)][AllowEmptyString()][string]$Argument)

    if ($Argument.Length -eq 0) {
        return '""'
    }
    if ($Argument -notmatch '[\s"]') {
        return $Argument
    }

    # Escape embedded double quotes the way the C runtime expects: \" -> \\"
    $escaped = $Argument -replace '(\\*)"', '$1$1\"'

    # A run of backslashes immediately before the closing quote would escape it,
    # so those are doubled. (Only matters for arguments ending in `\`.)
    $trailing = [Regex]::Match($escaped, '\\+$')
    if ($trailing.Success) {
        $escaped = $escaped.Substring(0, $escaped.Length - $trailing.Length) + ($trailing.Value * 2)
    }

    return '"' + $escaped + '"'
}

# Joins an argument array into a single correctly quoted command line.
function ConvertTo-CommandLine {
    param([string[]]$Arguments = @())

    $quoted = @()
    foreach ($argument in $Arguments) {
        $quoted += (ConvertTo-QuotedArgument -Argument ([string]$argument))
    }
    return ($quoted -join ' ')
}

function Assert-CommandExists {
    param([Parameter(Mandatory = $true)][string]$Name)
    $command = Get-Command -Name $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "Required command '$Name' was not found on PATH."
    }
    return $command
}

# --- version checks -----------------------------------------------------------
function Get-PythonVersionFromLauncher {
    # The owner's machine has Python 3.14 as default; `py -3.12` is explicit.
    $probe = "import sys;print('%d.%d.%d' % sys.version_info[:3])"
    $result = Get-NativeOutput -FilePath 'py' -Arguments @('-3.12', '-c', $probe)
    if ($result.ExitCode -ne 0) {
        return $null
    }
    return $result.Output
}

function Assert-Python312 {
    param([string]$Version)
    if (-not $Version) {
        throw @'
Python 3.12 was not found via the `py -3.12` launcher.

Install Python 3.12 (python.org, "Windows installer (64-bit)") and make sure the
Python Launcher for Windows is included. This project targets Python 3.12 only:
Python 3.14 is not supported by every pinned dependency, so never use the bare
`python` command on this machine.
'@
    }
    if (-not $Version.StartsWith($script:RequiredPython + '.')) {
        throw "Expected Python $($script:RequiredPython).x from 'py -3.12' but found $Version."
    }
    return $Version
}

function Test-NodeVersion {
    param([Parameter(Mandatory = $true)][string]$Version)
    # Vite 7 requires ^20.19.0 || >=22.12.0.
    $clean = $Version.TrimStart('v')
    $parts = $clean.Split('.')
    if ($parts.Length -lt 2) {
        return $false
    }
    $major = [int]$parts[0]
    $minor = [int]$parts[1]

    if ($major -eq 20) {
        return $minor -ge $script:MinNodeMinorForTwenty
    }
    if ($major -eq 21) {
        return $false
    }
    return ($major -ge $script:MinNodeMajorForTwentyTwo)
}

# --- process helpers ----------------------------------------------------------
# Only processes started by start.ps1 are ever stopped. Identity is verified by
# both PID and command line before any signal is sent.
function Get-ProcessCommandLine {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    try {
        $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $ProcessId" -ErrorAction Stop
        if ($process) {
            return [string]$process.CommandLine
        }
    }
    catch {
        return $null
    }
    return $null
}

# Returns a snapshot of ALL processes: ProcessId -> {ProcessId, ParentProcessId,
# Name, CommandLine, CreationDate, ExecutablePath}. One CIM query instead of one
# per PID, so a tree walk is a single consistent view.
function Get-ProcessSnapshot {
    $snapshot = @{}
    $processes = Get-CimInstance -ClassName Win32_Process -ErrorAction SilentlyContinue
    if (-not $processes) { return $snapshot }
    foreach ($process in $processes) {
        $snapshot[[int]$process.ProcessId] = [pscustomobject]@{
            ProcessId       = [int]$process.ProcessId
            ParentProcessId = [int]$process.ParentProcessId
            Name            = [string]$process.Name
            CommandLine     = [string]$process.CommandLine
            CreationDate    = $process.CreationDate
            ExecutablePath  = [string]$process.ExecutablePath
        }
    }
    return $snapshot
}

# Returns the PIDs of every descendant of $RootProcessId, breadth-first, using a
# snapshot. Never includes the root itself.
function Get-DescendantProcessIds {
    param(
        [Parameter(Mandatory = $true)][int]$RootProcessId,
        [Parameter(Mandatory = $false)]$Snapshot
    )
    if (-not $Snapshot) { $Snapshot = Get-ProcessSnapshot }

    $children = @{}
    foreach ($entry in $Snapshot.Values) {
        $parent = $entry.ParentProcessId
        if (-not $children.ContainsKey($parent)) {
            $children[$parent] = New-Object System.Collections.Generic.List[int]
        }
        $children[$parent].Add($entry.ProcessId)
    }

    $result = New-Object System.Collections.Generic.List[int]
    $queue = New-Object System.Collections.Generic.Queue[int]
    $queue.Enqueue($RootProcessId)
    while ($queue.Count -gt 0) {
        $current = $queue.Dequeue()
        if (-not $children.ContainsKey($current)) { continue }
        foreach ($child in $children[$current]) {
            if (-not $result.Contains($child)) {
                $result.Add($child)
                $queue.Enqueue($child)
            }
        }
    }
    return $result
}

# True when a live PID still corresponds to the process that was recorded:
# same PID, same name, and (when recorded) the same creation time. Creation time
# is what defeats PID reuse - Windows recycles PIDs aggressively.
function Test-ProcessIdentity {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId,
        [Parameter(Mandatory = $false)][string]$ExpectedName,
        [Parameter(Mandatory = $false)][string]$ExpectedCreationTime,
        [Parameter(Mandatory = $false)]$Snapshot
    )
    if (-not $Snapshot) { $Snapshot = Get-ProcessSnapshot }
    if (-not $Snapshot.ContainsKey($ProcessId)) { return $false }

    $entry = $Snapshot[$ProcessId]
    if ($ExpectedName -and $entry.Name -ne $ExpectedName) { return $false }
    if ($ExpectedCreationTime) {
        $actual = ConvertTo-CreationStamp -CreationDate $entry.CreationDate
        if ($actual -ne $ExpectedCreationTime) { return $false }
    }
    return $true
}

# Normalises a CIM CreationDate (DMTF string or DateTime) to a sortable string
# so it can be stored in JSON and compared later.
function ConvertTo-CreationStamp {
    param([Parameter(Mandatory = $false)]$CreationDate)
    if ($null -eq $CreationDate) { return '' }
    try {
        if ($CreationDate -is [datetime]) {
            return $CreationDate.ToUniversalTime().ToString('yyyyMMddHHmmss')
        }
        return ([Management.ManagementDateTimeConverter]::ToDateTime([string]$CreationDate)).ToUniversalTime().ToString('yyyyMMddHHmmss')
    }
    catch {
        return ''
    }
}

# True when the command line identifies THIS application's Vite dev server:
# a vite entry point under this repository's frontend directory.
function Test-ViteCommandLine {
    param([Parameter(Mandatory = $false)][string]$CommandLine)
    if (-not $CommandLine) { return $false }
    $frontendEscaped = [Regex]::Escape($script:FrontendDir)
    # vite.js / vite bin path anywhere in this repo's frontend directory.
    if ($CommandLine -match $frontendEscaped -and $CommandLine -match 'vite') { return $true }
    # node_modules/.bin or vite/bin/vite.js under our frontend, with either slash.
    $normalised = $CommandLine.Replace('/', '\')
    $frontendNormalised = $script:FrontendDir.Replace('/', '\')
    if ($normalised -match [Regex]::Escape($frontendNormalised) -and $normalised -match 'vite') { return $true }
    return $false
}

# True when the command line is this application's uvicorn backend.
function Test-UvicornCommandLine {
    param([Parameter(Mandatory = $false)][string]$CommandLine)
    if (-not $CommandLine) { return $false }
    return ($CommandLine -match 'uvicorn' -and $CommandLine -match 'app\.main:app')
}

# True when the command line is the npm wrapper that start.ps1 launched:
# any npm/npm.cmd invocation running the `dev` script with our frontend port.
function Test-NpmWrapperCommandLine {
    param(
        [Parameter(Mandatory = $false)][string]$CommandLine,
        [Parameter(Mandatory = $true)][int]$Port
    )
    if (-not $CommandLine) { return $false }
    $runsNpm = $CommandLine -match 'npm(\.cmd)?'
    $runsDev = $CommandLine -match 'run\s+dev'
    $usesPort = $CommandLine -match "--port\s+$Port\b"
    return ($runsNpm -and $runsDev -and $usesPort)
}

function Test-PortListening {
    param([Parameter(Mandatory = $true)][int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return ($null -ne $connection)
}

function Read-StateFile {
    if (-not (Test-Path -LiteralPath $script:StateFile)) {
        return $null
    }
    try {
        return (Get-Content -LiteralPath $script:StateFile -Raw | ConvertFrom-Json)
    }
    catch {
        Write-Warn "Could not parse $($script:StateFile); ignoring it."
        return $null
    }
}

function Wait-HttpOk {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [int]$TimeoutSeconds = 60,
        [int]$IntervalMilliseconds = 500
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                return $true
            }
        }
        catch {
            Start-Sleep -Milliseconds $IntervalMilliseconds
        }
    }
    return $false
}

function Ensure-RuntimeDir {
    if (-not (Test-Path -LiteralPath $script:RuntimeDir)) {
        New-Item -ItemType Directory -Path $script:RuntimeDir -Force | Out-Null
    }
    return $script:RuntimeDir
}

Write-Verbose "Repository root: $script:RepoRoot"

# Exported for dot-sourcing scripts (no module system: these are plain functions).
$script:CommonLoaded = $true
