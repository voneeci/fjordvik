<#
.SYNOPSIS
  Run DAX queries against the model open in Power BI Desktop and print the results as JSON.

.DESCRIPTION
  Power BI Desktop runs a local Analysis Services engine on a random port while a
  file is open. This script finds that port, loads the ADOMD.NET client library
  that ships with Power BI Desktop, runs each query (optionally as a security
  role), and prints one JSON object per query: id, value, error.

  Input: a JSON file holding a list of {"id": ..., "query": ..., "role": ...}.
  Read-only: it only runs EVALUATE queries.

.EXAMPLE
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts\run_dax.ps1 -QueryFile queries.json
#>
param(
    [Parameter(Mandatory = $true)][string]$QueryFile,
    [int]$Port = 0
)
$ErrorActionPreference = "Stop"

function Find-Port {
    # First choice: ask Windows which port the running engine (msmdsrv.exe) listens on.
    $engine = Get-CimInstance Win32_Process -Filter "Name='msmdsrv.exe'" | Select-Object -First 1
    if ($engine) {
        $listen = Get-NetTCPConnection -OwningProcess $engine.ProcessId -State Listen -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($listen) { return [int]$listen.LocalPort }
    }
    # Fallback: the port file Desktop writes into its workspace folder. The Microsoft
    # Store version uses %USERPROFILE%\Microsoft\Power BI Desktop Store App.
    $roots = @(
        "$env:USERPROFILE\Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces",
        "$env:LOCALAPPDATA\Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces",
        "$env:LOCALAPPDATA\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces"
    )
    $files = foreach ($r in $roots) {
        if (Test-Path $r) { Get-ChildItem -Path $r -Recurse -Filter "msmdsrv.port.txt" -ErrorAction SilentlyContinue }
    }
    $latest = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) { throw "No open Power BI Desktop model found. Open FjordvikEmissions.pbip first." }
    # The port file is written as UTF-16 text.
    return [int]((Get-Content -Path $latest.FullName -Encoding Unicode -Raw).Trim())
}

function Find-Adomd {
    $pkg = Get-AppxPackage -Name "Microsoft.MicrosoftPowerBIDesktop" -ErrorAction SilentlyContinue
    $candidates = @()
    if ($pkg) { $candidates += Join-Path $pkg.InstallLocation "bin\Microsoft.PowerBI.AdomdClient.dll" }
    $candidates += "$env:ProgramFiles\Microsoft Power BI Desktop\bin\Microsoft.PowerBI.AdomdClient.dll"
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    throw "ADOMD client library not found. Is Power BI Desktop installed?"
}

if ($Port -eq 0) { $Port = Find-Port }
Add-Type -Path (Find-Adomd)

$queries = Get-Content -Path $QueryFile -Raw | ConvertFrom-Json
$results = @()
foreach ($q in $queries) {
    $cs = "Data Source=localhost:$Port"
    if ($q.role) { $cs += ";Roles=$($q.role)" }
    $conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection($cs)
    try {
        $conn.Open()
        $cmd = $conn.CreateCommand()
        $cmd.CommandText = $q.query
        $reader = $cmd.ExecuteReader()
        $value = $null
        if ($reader.Read()) {
            if (-not $reader.IsDBNull(0)) { $value = [double]$reader.GetValue(0) }
        }
        $reader.Close()
        $results += [pscustomobject]@{ id = $q.id; value = $value; error = $null }
    }
    catch {
        $results += [pscustomobject]@{ id = $q.id; value = $null; error = $_.Exception.Message }
    }
    finally { $conn.Close() }
}
ConvertTo-Json -InputObject @($results) -Depth 3 -Compress
