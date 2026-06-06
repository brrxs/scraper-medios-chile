param(
    [string]$Version = "0.3",
    [string]$Name    = "PressCL"
)

$src     = $PSScriptRoot
$zipName = "$Name-v$Version.zip"
$out     = Join-Path $src $zipName

if (Test-Path $out) { Remove-Item $out -Force }

$excludeDirs  = @('.git', '.venv', '__pycache__', 'datos', 'logs', 'reports', 'analisis')
$excludeFiles = @($zipName, 'build_release.bat', 'build_release.ps1', 'TODO.md', 'bug_report.md', 'presscl.gif', 'PressCL.lnk', 'Detener Scraper.lnk', 'Abrir Scraper de Prensa.lnk')
$excludeExts  = @('.pyc', '.pyo', '.log')

Add-Type -Assembly System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($out, 'Create')

Get-ChildItem -Path $src -Recurse -File | Where-Object {
    $rel   = $_.FullName.Substring($src.Length).TrimStart('\', '/')
    $parts = $rel -split '[/\\]'
    $inExcludedDir  = ($parts | Select-Object -SkipLast 1) | Where-Object { $_ -in $excludeDirs }
    $isExcludedFile = $_.Name -in $excludeFiles
    $isExcludedExt  = $_.Extension -in $excludeExts
    -not ($inExcludedDir -or $isExcludedFile -or $isExcludedExt)
} | ForEach-Object {
    $entry = $_.FullName.Substring($src.Length).TrimStart('\', '/').Replace('\', '/')
    [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $_.FullName, $entry) | Out-Null
}

$zip.Dispose()
Write-Host "Done: $zipName ($([math]::Round((Get-Item $out).Length / 1MB, 1)) MB)"
Write-Host "Attach this file to the GitHub release for v$Version."
