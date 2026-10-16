param([Parameter(Mandatory=$true)][string]$QueryFile, [Parameter(Mandatory=$true)][int]$Port, [switch]$Refresh)
$ErrorActionPreference = "Stop"
$pkg = Get-AppxPackage -Name "Microsoft.MicrosoftPowerBIDesktop"
Add-Type -Path (Join-Path $pkg.InstallLocation "bin\Microsoft.PowerBI.AdomdClient.dll")
$conn = New-Object Microsoft.AnalysisServices.AdomdClient.AdomdConnection("Data Source=localhost:$Port")
$conn.Open()
if ($Refresh) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = "SELECT [CATALOG_NAME] FROM `$SYSTEM.DBSCHEMA_CATALOGS"
    $r = $cmd.ExecuteReader(); $r.Read() | Out-Null; $db = $r.GetValue(0); $r.Close()
    $cmd.CommandText = '{"refresh":{"type":"full","objects":[{"database":"' + $db + '"}]}}'
    $cmd.ExecuteNonQuery() | Out-Null
    "refreshed database $db"
}
$queries = Get-Content -Path $QueryFile -Raw | ConvertFrom-Json
foreach ($q in $queries) {
    "=== $($q.id)"
    try {
        $cmd = $conn.CreateCommand(); $cmd.CommandText = $q.query
        $r = $cmd.ExecuteReader(); $n = 0
        while ($r.Read()) {
            $n++
            $vals = for ($i = 0; $i -lt $r.FieldCount; $i++) { "$($r.GetName($i))=$(if ($r.IsDBNull($i)) {'BLANK'} else {$r.GetValue($i)})" }
            if ($n -le 8) { $vals -join " | " }
        }
        $r.Close(); "rows: $n"
    } catch { "ERROR: $($_.Exception.Message)" }
}
$conn.Close()
