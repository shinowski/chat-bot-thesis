$ErrorActionPreference = 'Stop'
$statePath = Join-Path $PSScriptRoot '.logs\share-state.json'
if (-not (Test-Path -LiteralPath $statePath)) {
    & (Join-Path $PSScriptRoot 'update-sharing-readme.ps1')
    Write-Host 'Sharing is not running.'
    exit 0
}
$state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
$tunnel = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
if ($tunnel) {
    $expectedPath = Join-Path $PSScriptRoot '.tools\cloudflared.exe'
    if ($tunnel.Path -ne $expectedPath -or
        $tunnel.StartTime.ToUniversalTime().Ticks -ne [long]$state.start_ticks) {
        throw 'The saved sharing process does not match. No process was stopped.'
    }
    Stop-Process -Id $tunnel.Id
}
Remove-Item -LiteralPath $statePath
& (Join-Path $PSScriptRoot 'update-sharing-readme.ps1')
Write-Host 'Sharing stopped. The online link no longer works. Flamma can still be used locally.'
