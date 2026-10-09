# Create a temporary HTTPS link to the running Flamma app.
$ErrorActionPreference = 'Stop'
$logPath = Join-Path $PSScriptRoot '.logs'
$toolPath = Join-Path $PSScriptRoot '.tools'
$cloudflaredPath = Join-Path $toolPath 'cloudflared.exe'
$statePath = Join-Path $logPath 'share-state.json'

if (Test-Path -LiteralPath $statePath) {
    try {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        $existing = Get-Process -Id ([int]$state.pid) -ErrorAction Stop
        if ($existing.Path -eq $cloudflaredPath -and
            $existing.StartTime.ToUniversalTime().Ticks -eq [long]$state.start_ticks -and
            $state.url -match '^https://[a-z0-9-]+\.trycloudflare\.com$') {
            & (Join-Path $PSScriptRoot 'update-sharing-readme.ps1') -Url $state.url
            Write-Host "Sharing is already running. Send this link to your groupmates: $($state.url)"
            Write-Host 'Keep this computer on and connected to the internet.'
            exit 0
        }
    } catch { }
    Remove-Item -LiteralPath $statePath
}

# The image API stays on localhost. Browsers use Flamma, which forwards photos.
& (Join-Path $PSScriptRoot 'start.ps1')
New-Item -ItemType Directory -Path $logPath, $toolPath -Force | Out-Null
if (-not (Test-Path -LiteralPath $cloudflaredPath)) {
    Write-Host 'Downloading the official Cloudflare sharing tool...'
    $release = Invoke-RestMethod -Uri 'https://api.github.com/repos/cloudflare/cloudflared/releases/latest' -TimeoutSec 30
    $assetName = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'cloudflared-windows-arm64.exe' } else { 'cloudflared-windows-amd64.exe' }
    $asset = $release.assets | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
    if (-not $asset -or $asset.browser_download_url -notmatch '^https://github\.com/cloudflare/cloudflared/releases/download/') {
        throw 'The official Windows download was not found. See README.md.'
    }
    if ($asset.digest -notmatch '^sha256:([a-f0-9]{64})$') {
        throw 'The official release has no SHA-256 checksum. See README.md.'
    }
    $expectedHash = $Matches[1]
    $downloadPath = Join-Path $toolPath 'cloudflared.download'
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $asset.browser_download_url -OutFile $downloadPath -TimeoutSec 180
        if ((Get-FileHash -LiteralPath $downloadPath -Algorithm SHA256).Hash -ne $expectedHash) {
            throw 'The sharing tool download did not match its official checksum.'
        }
        Move-Item -LiteralPath $downloadPath -Destination $cloudflaredPath
    } finally {
        if (Test-Path -LiteralPath $downloadPath) { Remove-Item -LiteralPath $downloadPath }
    }
}

$outputLog = Join-Path $logPath 'share.log'
$errorLog = Join-Path $logPath 'share.error.log'
$tunnel = Start-Process -FilePath $cloudflaredPath -ArgumentList @(
    'tunnel', '--no-autoupdate', '--url', 'http://127.0.0.1:5000',
    '--protocol', 'http2', '--metrics', '127.0.0.1:0'
) -WindowStyle Hidden -PassThru -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog
$state = [ordered]@{ pid = $tunnel.Id; start_ticks = $tunnel.StartTime.ToUniversalTime().Ticks; url = $null }
$state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
$ready = $false
$connectedAt = $null
try {
    Write-Host 'Creating your sharing link...'
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        $tunnel.Refresh()
        if ($tunnel.HasExited) { throw "Sharing stopped unexpectedly. Check $errorLog." }
        $logs = (Get-Content -LiteralPath $errorLog -Raw -ErrorAction SilentlyContinue) +
                (Get-Content -LiteralPath $outputLog -Raw -ErrorAction SilentlyContinue)
        if (-not $state.url) {
            if ($logs -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
                $state.url = $Matches[0]
                $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
            }
        }
        if (-not $connectedAt -and $logs -match 'Registered tunnel connection') {
            $connectedAt = [DateTime]::UtcNow
        }
        # Allow the tunnel and its DNS record to register before resolving its
        # new hostname; an early failed lookup can be cached by Windows DNS.
        if ($state.url -and $connectedAt -and ([DateTime]::UtcNow - $connectedAt).TotalSeconds -ge 5) {
            try {
                $health = Invoke-RestMethod -Uri "$($state.url)/health" -TimeoutSec 3
                if ($health.status -eq 'ok' -and $health.service -eq 'flamma' -and
                    $health.app_path -eq (Join-Path $PSScriptRoot 'Flamma\app.py')) {
                    $ready = $true
                    break
                }
            } catch { }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "The sharing link did not become ready. Check $errorLog and your internet connection." }
    & (Join-Path $PSScriptRoot 'update-sharing-readme.ps1') -Url $state.url
    Write-Host ''
    Write-Host "Send this link to your groupmates: $($state.url)"
    Write-Host 'This link is also saved at the top of README.md.'
    Write-Host 'They can chat and upload photos without installing anything.'
    Write-Host 'Keep this computer on and connected to the internet. Each browser has its own chat history.'
    Write-Host 'Anyone with the link can use the app. A new sharing session creates a new link.'
    Write-Host 'To stop sharing: powershell -ExecutionPolicy Bypass -File .\stop-sharing.ps1'
} catch {
    & (Join-Path $PSScriptRoot 'stop-sharing.ps1')
    throw
}
