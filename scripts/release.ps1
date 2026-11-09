param(
    [string]$Version = "",
    [switch]$SkipTests,
    [switch]$NoPush
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = if ($env:NOCTIS_PYTHON) { $env:NOCTIS_PYTHON } else { "py" }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git est introuvable. Installe Git pour Windows."
}
if (-not (Test-Path ".git")) {
    throw "Ce dossier n'est pas encore un dépôt Git. Lance 'git init' d'abord."
}

if (-not $Version) {
    $Version = (Get-Content "VERSION" -Raw).Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') {
    throw "Version invalide : $Version"
}

Write-Host "== Vérification de la version ==" -ForegroundColor Cyan
& $Python "scripts/bump_version.py" $Version
& $Python "scripts/check_version.py"
if ($LASTEXITCODE -ne 0) { throw "Version incohérente." }

if (-not $SkipTests) {
    Write-Host "== Tests ==" -ForegroundColor Cyan
    & $Python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "Les tests ont échoué." }
}

Write-Host "== Commit et tag ==" -ForegroundColor Cyan
git add -A
$pending = git status --porcelain
if ($pending) {
    git commit -m "Release v$Version"
} else {
    Write-Host "Aucune modification à committer."
}

$existing = git tag -l "v$Version"
if ($existing) {
    throw "Le tag v$Version existe déjà."
}
git tag "v$Version"

if (-not $NoPush) {
    Write-Host "== Publication ==" -ForegroundColor Cyan
    git push origin HEAD
    git push origin "v$Version"
    Write-Host "Tag v$Version envoyé : GitHub Actions va compiler et publier l'installateur." -ForegroundColor Green
} else {
    Write-Host "Tag local v$Version créé (aucun push demandé)." -ForegroundColor Yellow
}
