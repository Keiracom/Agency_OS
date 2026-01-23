# Plasmic Sync Script for Agency OS
# Run from frontend directory: .\scripts\plasmic-sync.ps1

Write-Host "Syncing Plasmic components..." -ForegroundColor Cyan

# Check if plasmic.json exists
if (-not (Test-Path "plasmic.json")) {
    Write-Host "Error: plasmic.json not found. Run from frontend directory." -ForegroundColor Red
    exit 1
}

# Run sync
npx @plasmicapp/cli sync --yes

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nSync complete! Components are in components/plasmic/" -ForegroundColor Green
} else {
    Write-Host "`nSync failed. Make sure you have components in Plasmic Studio." -ForegroundColor Yellow
    Write-Host "Open: https://studio.plasmic.app/projects/sTVtoZDhkmD2Edyr9vqjyS" -ForegroundColor Cyan
}
