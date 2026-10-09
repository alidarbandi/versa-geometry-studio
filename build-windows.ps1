param([string]$OutputDirectory = 'dist')

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$outputPath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot $OutputDirectory))
$workspacePrefix = $PSScriptRoot.TrimEnd('\') + '\'
if (-not $outputPath.StartsWith($workspacePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'The build output directory must be inside this repository.'
}
$exePath = Join-Path $outputPath 'VersaGeometryStudio\VersaGeometryStudio.exe'
if (Get-Process -Name VersaGeometryStudio -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $exePath }) {
    throw 'This build is running. Close it or use -OutputDirectory release\build.'
}
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Create the .venv environment and install .[dev] first. See README.md.' }
& $pythonPath -m pytest -q
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $pythonPath -m PyInstaller --noconfirm --distpath $outputPath packaging\VersaGeometryStudio.spec
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
$screenshotPath = Join-Path $PSScriptRoot 'artifacts\packaged-smoke.png'
$process = Start-Process -FilePath $exePath -ArgumentList @('--smoke-test', ('"' + $screenshotPath + '"')) -PassThru -WindowStyle Hidden
if (-not $process.WaitForExit(30000)) { $process.Kill(); throw 'Packaged application smoke check timed out' }
if ($process.ExitCode -ne 0) { throw "Packaged app failed with exit code $($process.ExitCode)" }
Write-Host "Built and launched: $exePath"
