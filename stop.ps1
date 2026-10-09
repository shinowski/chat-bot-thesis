$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.logs\share-state.json')) {
    & (Join-Path $PSScriptRoot 'stop-sharing.ps1')
}
$serviceSpecs = @(
    @{ Name = 'flamma'; Service = 'flamma'; Port = 5000; Directory = 'Flamma' },
    @{ Name = 'image'; Service = 'flamma-image'; Port = 8000; Directory = 'Image\thesis-backend' }
)
foreach ($serviceSpec in $serviceSpecs) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$($serviceSpec.Port)/health" -TimeoutSec 3
    } catch {
        Write-Host "$($serviceSpec.Name) is not responding. No process was stopped."
        continue
    }
    $expectedAppPath = Join-Path (Join-Path $PSScriptRoot $serviceSpec.Directory) 'app.py'
    if ($health.service -ne $serviceSpec.Service -or $health.app_path -ne $expectedAppPath -or -not $health.pid) {
        Write-Host "Port $($serviceSpec.Port) belongs to an unrecognized service. No process was stopped."
        continue
    }
    Stop-Process -Id ([int]$health.pid) -ErrorAction SilentlyContinue
    Write-Host "$($serviceSpec.Name) stopped."
}
