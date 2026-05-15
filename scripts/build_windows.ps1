$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not (Test-Path -LiteralPath ".\.venv\Scripts\python.exe")) {
    python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

if (Test-Path -LiteralPath ".\build") {
    Remove-Item -LiteralPath ".\build" -Recurse -Force
}
if (Test-Path -LiteralPath ".\dist\LegalAnonymizer") {
    Remove-Item -LiteralPath ".\dist\LegalAnonymizer" -Recurse -Force
}

.\.venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --windowed `
    --name "LegalAnonymizer" `
    --paths "src" `
    "src\legal_anonymizer\__main__.py"

Copy-Item -LiteralPath ".\LAWYER_USAGE.md" -Destination ".\dist\LegalAnonymizer\LAWYER_USAGE.md" -Force

if (Test-Path -LiteralPath ".\dist\LegalAnonymizer.zip") {
    Remove-Item -LiteralPath ".\dist\LegalAnonymizer.zip" -Force
}
Compress-Archive -LiteralPath ".\dist\LegalAnonymizer" -DestinationPath ".\dist\LegalAnonymizer.zip" -Force

Write-Host "Build output: $ProjectRoot\dist\LegalAnonymizer\LegalAnonymizer.exe"
Write-Host "Zip output: $ProjectRoot\dist\LegalAnonymizer.zip"
