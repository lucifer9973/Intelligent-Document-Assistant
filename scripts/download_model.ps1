<#
PowerShell helper to download a model file into C:\models\llama (or custom dir).

Usage:
  # Interactive: prompts for URL
  .\scripts\download_model.ps1

  # Non-interactive: pass URL and dest
  .\scripts\download_model.ps1 -Url "https://example.com/model.bin" -Dest "C:\models\llama"

Notes:
 - Use a direct download URL (not an HTML page). If the host requires cookies/auth, download manually.
 - This script does a simple download and reports progress.
#>

param(
    [string]$Url,
    [string]$Dest = "C:\models\llama"
)

function Ensure-Dir([string]$path) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
}

if (-not $Url) {
    $Url = Read-Host "Enter direct model download URL (or paste link)"
}

if (-not $Url) {
    Write-Error "No URL provided. Aborting."
    exit 1
}

Ensure-Dir $Dest

$fileName = Split-Path $Url -Leaf
$outPath = Join-Path $Dest $fileName

Write-Host "Downloading model to: $outPath"

try {
    Invoke-WebRequest -Uri $Url -OutFile $outPath -UseBasicParsing -Verbose
    Write-Host "Download complete: $outPath"
} catch {
    Write-Error "Download failed: $_"
    if (Test-Path $outPath) { Remove-Item $outPath -Force }
    exit 1
}

Write-Host "Set the environment variable (PowerShell session):"
Write-Host "`$Env:LOCAL_LLM_MODEL_PATH = '$outPath'"
