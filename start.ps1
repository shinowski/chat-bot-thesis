param([string]$PythonPath)

$ErrorActionPreference = 'Stop'
$workspacePath = $PSScriptRoot
if (-not $PythonPath) {
    $PythonPath = Join-Path $workspacePath 'Flamma\venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw 'Python environment not found. Follow README.md to install dependencies, or pass -PythonPath.'
}
$serviceSpecs = @(
    @{ Name = 'image'; Service = 'flamma-image'; Port = 8000; Directory = 'Image\thesis-backend' },
    @{ Name = 'flamma'; Service = 'flamma'; Port = 5000; Directory = 'Flamma' }
)
$servicesToStart = @()
# Check both ports before launching either service. Never stop unrelated apps.
foreach ($serviceSpec in $serviceSpecs) {
    $portProbe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $serviceSpec.Port)
    $portAvailable = $false
    try { $portProbe.Start(); $portAvailable = $true }
    catch { $portAvailable = $false }
    finally { $portProbe.Stop() }
    if ($portAvailable) {
        $servicesToStart += $serviceSpec
        continue
    }
    $health = $null
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$($serviceSpec.Port)/health" -TimeoutSec 3
    } catch { }
    $expectedAppPath = Join-Path (Join-Path $workspacePath $serviceSpec.Directory) 'app.py'
    if ($health -and $health.status -eq 'ok' -and $health.service -eq $serviceSpec.Service -and $health.app_path -eq $expectedAppPath) {
        Write-Host "$($serviceSpec.Name) is already running (PID $($health.pid))."
    } else {
        throw "Port $($serviceSpec.Port) is occupied by an unrecognized service. Close that service or use a different port."
    }
}
$logPath = Join-Path $workspacePath '.logs'
New-Item -ItemType Directory -Path $logPath -Force | Out-Null
$startedServices = @()
try {
    foreach ($serviceSpec in $servicesToStart) {
        $process = Start-Process -FilePath $PythonPath -ArgumentList @('-u', '-B', 'app.py') `
            -WorkingDirectory (Join-Path $workspacePath $serviceSpec.Directory) -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput (Join-Path $logPath ($serviceSpec.Name + '.log')) `
            -RedirectStandardError (Join-Path $logPath ($serviceSpec.Name + '.error.log'))
        $startedServices += $process
        $expectedAppPath = Join-Path (Join-Path $workspacePath $serviceSpec.Directory) 'app.py'
        $ready = $false
        for ($attempt = 0; $attempt -lt 60; $attempt++) {
            $process.Refresh()
            if ($process.HasExited) {
                throw "$($serviceSpec.Name) failed to start. Check $logPath\$($serviceSpec.Name).error.log."
            }
            try {
                $health = Invoke-RestMethod -Uri "http://127.0.0.1:$($serviceSpec.Port)/health" -TimeoutSec 1
                if ($health.status -eq 'ok' -and $health.service -eq $serviceSpec.Service -and $health.app_path -eq $expectedAppPath) {
                    $ready = $true
                    break
                }
            } catch { }
            Start-Sleep -Milliseconds 500
        }
        if (-not $ready) {
            throw "$($serviceSpec.Name) did not become ready. Check $logPath\$($serviceSpec.Name).error.log."
        }
        Write-Host "$($serviceSpec.Name) started (PID $($process.Id))."
    }
} catch {
    foreach ($process in $startedServices) {
        $process.Refresh()
        if (-not $process.HasExited) { $process.Kill() }
    }
    throw
}
Write-Host 'Open http://127.0.0.1:5000 to chat and upload a skin image.'
Write-Host "Logs: $logPath"
Write-Host 'To stop both services: powershell -ExecutionPolicy Bypass -File .\stop.ps1'
