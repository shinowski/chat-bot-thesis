# Keep the README's online link in sync with the sharing session.
param([string]$Url)

$ErrorActionPreference = 'Stop'
if ($Url -and $Url -notmatch '^https://[a-z0-9-]+\.trycloudflare\.com$') {
    throw 'The sharing URL is invalid.'
}
$readmePath = Join-Path $PSScriptRoot 'README.md'
$readme = [System.IO.File]::ReadAllText($readmePath)
$startMarker = '<!-- flamma-sharing:start -->'
$endMarker = '<!-- flamma-sharing:end -->'
$startIndex = $readme.IndexOf($startMarker, [System.StringComparison]::Ordinal)
$endIndex = $readme.IndexOf($endMarker, [System.StringComparison]::Ordinal)
if ($startIndex -lt 0 -or $endIndex -lt ($startIndex + $startMarker.Length)) {
    throw 'The sharing link section is missing from README.md.'
}
$newLine = if ($readme.Contains("`r`n")) { "`r`n" } else { "`n" }
if ($Url) {
    $status = '**[Open Flamma]({url})**'.Replace('{url}', $Url) + $newLine + $newLine +
        'Current online address: [{url}]({url})'.Replace('{url}', $Url) + $newLine + $newLine +
        '**Sharing is running.** This temporary link works while the host computer and sharing service are running.'
} else {
    $status = '**Sharing is stopped.** Follow the online sharing tutorial below to create a new link.'
}
$updatedReadme = $readme.Substring(0, $startIndex + $startMarker.Length) +
    $newLine + $status + $newLine + $readme.Substring($endIndex)
[System.IO.File]::WriteAllText($readmePath, $updatedReadme, [System.Text.UTF8Encoding]::new($false))
