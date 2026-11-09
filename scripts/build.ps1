param(
    [switch]$SkipDeps,
    [switch]$SkipTests,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not $Python) {
    $Python = $env:NOCTIS_PYTHON
}
if (-not $Python) {
    if (Get-Command py -ErrorAction SilentlyContinue) { $Python = "py" }
    elseif (Get-Command python -ErrorAction SilentlyContinue) { $Python = "python" }
    else { throw "Python est introuvable. Installe Python 3.11 ou plus récent." }
}

$pythonArgs = @()
if ($Python -eq "py") { $pythonArgs = @("-3") }

function Invoke-Py {
    param([string[]]$PyArgs)
    & $Python @pythonArgs @PyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "La commande Python a échoué (code $LASTEXITCODE) : $($PyArgs -join ' ')"
    }
}

Write-Host "== Vérification de la version ==" -ForegroundColor Cyan
Invoke-Py -PyArgs @("scripts/check_version.py")

if (-not $SkipTests) {
    Write-Host "== Tests ==" -ForegroundColor Cyan
    Invoke-Py -PyArgs @("-m", "unittest", "discover", "-s", "tests", "-v")
}

if (-not $SkipDeps) {
    Write-Host "== Dépendances ==" -ForegroundColor Cyan
    Invoke-Py -PyArgs @("-m", "pip", "install", "-r", "requirements-build.txt", "--disable-pip-version-check")
}

Write-Host "== Application (onefile, sans console) ==" -ForegroundColor Cyan
Invoke-Py -PyArgs @("-m", "PyInstaller", "--noconfirm", "--clean",
    "--distpath", "dist", "--workpath", "build/app", "packaging/NoctisAuth.spec")

Write-Host "== Installateur autonome ==" -ForegroundColor Cyan
Invoke-Py -PyArgs @("-m", "PyInstaller", "--noconfirm", "--clean",
    "--distpath", "dist", "--workpath", "build/setup", "packaging/NoctisAuth_Setup.spec")

Write-Host "== Empreintes SHA-256 ==" -ForegroundColor Cyan
Invoke-Py -PyArgs @("scripts/make_checksum.py")

$setup = Join-Path $Root "dist/NoctisAuth_Setup.exe"
$app = Join-Path $Root "dist/NoctisAuth.exe"
if (-not (Test-Path $setup)) { throw "NoctisAuth_Setup.exe est introuvable." }
if (-not (Test-Path $app)) { throw "NoctisAuth.exe est introuvable." }

$setupHash = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
$published = (Get-Content "$setup.sha256" -Raw).Trim().Split()[0]
if ($setupHash -ne $published) { throw "L'empreinte SHA-256 de l'installateur est invalide." }

Write-Host ""
Write-Host "Compilation terminée :" -ForegroundColor Green
Write-Host ("  dist/NoctisAuth.exe         {0:N1} Mo" -f ((Get-Item $app).Length / 1MB))
Write-Host ("  dist/NoctisAuth_Setup.exe   {0:N1} Mo" -f ((Get-Item $setup).Length / 1MB))
Write-Host ("  SHA-256                     {0}" -f $setupHash)
Write-Host ""
Write-Host "Lance dist/NoctisAuth_Setup.exe pour tester l'installation." -ForegroundColor Yellow
