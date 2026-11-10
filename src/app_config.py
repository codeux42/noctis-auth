"""Configuration centrale de Noctis Auth.

Ce module est la source de vérité pour la version de l'application et pour le
dépôt GitHub utilisé par le système de mises à jour.

Pour publier une nouvelle version, utilise simplement :

    py scripts/bump_version.py 2.9.1

La CI vérifie que le tag Git (v2.9.1), le fichier VERSION et ce module sont
tous alignés avant de produire un installateur.
"""

from __future__ import annotations

APP_NAME = "Noctis Auth"
APP_VERSION = "2.9.1"
APP_EXE = "NoctisAuth.exe"
SETUP_EXE = "NoctisAuth_Setup.exe"
APP_ID = "Noctis.Auth.Desktop"
SETUP_ID = "Noctis.Auth.Setup"

# Dépôt public utilisé pour les mises à jour (API GitHub Releases).
# Laisse GITHUB_OWNER vide tant que le dépôt n'existe pas : l'application
# désactivera alors proprement la vérification des mises à jour.
# scripts/configure_repo.py permet de renseigner ces valeurs sans éditer le code.
GITHUB_OWNER = "codeux42"
GITHUB_REPO = "noctis-auth"

UPDATE_CHECK_TIMEOUT = 8
UPDATE_USER_AGENT = f"NoctisAuth/{APP_VERSION} (+https://github.com/{GITHUB_OWNER or 'noctis'}/{GITHUB_REPO})"


def github_configured() -> bool:
    """Indique si un dépôt GitHub exploitable est configuré."""
    return bool(GITHUB_OWNER.strip()) and bool(GITHUB_REPO.strip())


def releases_api_url() -> str:
    return f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def releases_page_url() -> str:
    return f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases"
