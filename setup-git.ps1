# Script de mise en place du dépôt NotePro
# Clic droit > "Exécuter avec PowerShell" (ou lancer depuis PowerShell dans ce dossier)
Set-Location -Path $PSScriptRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git n'est pas installé : https://git-scm.com/download/win" -ForegroundColor Red
    Read-Host "Appuie sur Entrée pour quitter"; exit 1
}

if (-not (Test-Path ".git")) { git init }
git add README.md
git commit -m "first commit"
git branch -M main
if (-not (git remote | Select-String -Quiet "^origin$")) {
    git remote add origin https://github.com/cheickti13-cloud/NotePro.git
}
git push -u origin main

Write-Host "`nTerminé. Dépôt : https://github.com/cheickti13-cloud/NotePro" -ForegroundColor Green
Read-Host "Appuie sur Entrée pour fermer"
