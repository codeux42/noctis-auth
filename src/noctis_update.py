"""Vérification des mises à jour Noctis Auth via les GitHub Releases.

Ce module ne manipule jamais le coffre-fort, les clés TOTP ou le mot de passe.
Il effectue uniquement des requêtes HTTPS publiques vers l'API GitHub, puis
télécharge l'installateur signé par son empreinte SHA-256 publiée.

Aucune donnée personnelle, aucun identifiant et aucun secret ne sont envoyés.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app_config import (
    APP_VERSION,
    SETUP_EXE,
    UPDATE_CHECK_TIMEOUT,
    UPDATE_USER_AGENT,
    github_configured,
    releases_api_url,
    releases_page_url,
)

CHUNK_SIZE = 256 * 1024
ProgressCallback = Callable[[int, int], None]


class UpdateError(RuntimeError):
    """Erreur lisible par l'utilisateur, sans détail sensible."""


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag: str
    name: str
    notes: str
    page_url: str
    published_at: str
    setup_url: str
    setup_name: str
    sha256_url: str | None
    size: int


# ---------------------------------------------------------------------------
# Versions
# ---------------------------------------------------------------------------
def parse_version(text: str) -> tuple[int, ...]:
    """Transforme ``v2.9.1`` ou ``2.9.1-beta`` en tuple comparable."""
    match = re.search(r"(\d+(?:\.\d+){0,3})", text or "")
    if not match:
        return (0, 0, 0, 0)
    parts = [int(part) for part in match.group(1).split(".")]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def is_newer(latest: str, current: str = APP_VERSION) -> bool:
    return parse_version(latest) > parse_version(current)


# ---------------------------------------------------------------------------
# API GitHub
# ---------------------------------------------------------------------------
def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": UPDATE_USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


def _read_json(url: str, timeout: int = UPDATE_CHECK_TIMEOUT) -> dict:
    try:
        with urllib.request.urlopen(_request(url), timeout=timeout) as response:
            payload = response.read(2 * 1024 * 1024)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError(
                "Aucune version publiée n’a été trouvée sur le dépôt GitHub."
            ) from exc
        if exc.code == 403:
            raise UpdateError(
                "GitHub limite temporairement les vérifications. Réessaie plus tard."
            ) from exc
        raise UpdateError(f"GitHub a répondu avec le code {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise UpdateError(
            "Impossible de joindre GitHub. Vérifie ta connexion Internet."
        ) from exc
    except TimeoutError as exc:
        raise UpdateError("GitHub met trop de temps à répondre.") from exc
    try:
        return json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise UpdateError("La réponse de GitHub est illisible.") from exc


def _pick_asset(assets: list[dict], wanted: str) -> dict | None:
    wanted_lower = wanted.lower()
    for asset in assets:
        if str(asset.get("name", "")).lower() == wanted_lower:
            return asset
    # Compatibilité avec l'ancien nom « NoctisAuth-Setup.exe ».
    for asset in assets:
        name = str(asset.get("name", "")).lower()
        if name.endswith("setup.exe") and "noctis" in name:
            return asset
    return None


def fetch_latest_release(timeout: int = UPDATE_CHECK_TIMEOUT) -> ReleaseInfo | None:
    """Retourne la dernière version publiée, ou ``None`` si non configuré."""
    if not github_configured():
        return None
    data = _read_json(releases_api_url(), timeout=timeout)
    tag = str(data.get("tag_name") or "")
    version = tag.lstrip("vV") or str(data.get("name") or "")
    version = re.sub(r"[^0-9.].*$", "", version) or "0.0.0"
    assets = data.get("assets") or []
    setup = _pick_asset(assets, SETUP_EXE)
    if setup is None:
        raise UpdateError("Cette version ne contient pas d’installateur Windows.")
    sha = _pick_asset(assets, SETUP_EXE + ".sha256")
    if sha is None:
        raise UpdateError(
            "L’installateur publié ne possède pas d’empreinte SHA-256 : "
            "mise à jour refusée par sécurité."
        )
    return ReleaseInfo(
        version=version,
        tag=tag,
        name=str(data.get("name") or f"Noctis Auth {version}"),
        notes=str(data.get("body") or ""),
        page_url=str(data.get("html_url") or releases_page_url()),
        published_at=str(data.get("published_at") or ""),
        setup_url=str(setup.get("browser_download_url") or ""),
        setup_name=str(setup.get("name") or SETUP_EXE),
        sha256_url=str(sha.get("browser_download_url") or ""),
        size=int(setup.get("size") or 0),
    )


# ---------------------------------------------------------------------------
# Téléchargement et vérification d'intégrité
# ---------------------------------------------------------------------------
def _parse_sha256(text: str) -> str:
    match = re.search(r"\b([a-fA-F0-9]{64})\b", text or "")
    if not match:
        raise UpdateError("L’empreinte SHA-256 publiée est invalide.")
    return match.group(1).lower()


def fetch_expected_sha256(release: ReleaseInfo, timeout: int = 20) -> str:
    if not release.sha256_url:
        raise UpdateError("Empreinte SHA-256 introuvable pour cette version.")
    try:
        with urllib.request.urlopen(_request(release.sha256_url), timeout=timeout) as response:
            content = response.read(64 * 1024).decode("utf-8", "replace")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UpdateError("Impossible de télécharger l’empreinte de sécurité.") from exc
    return _parse_sha256(content)


def download_and_verify(
    release: ReleaseInfo,
    dest_dir: Path | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    """Télécharge l'installateur, vérifie son SHA-256 puis le rend exécutable.

    Le fichier n'est déplacé vers son nom final qu'après validation complète :
    un téléchargement interrompu ou corrompu n'est jamais exécuté.
    """
    if dest_dir is None:
        base = Path(os.getenv("LOCALAPPDATA", str(Path.home())))
        dest_dir = base / "NoctisAuth" / "Updates"
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_name = Path(release.setup_name).name or SETUP_EXE
    target = dest_dir / safe_name
    partial = target.with_name(target.name + ".part")

    expected = fetch_expected_sha256(release)
    digest = hashlib.sha256()
    done = 0
    try:
        with urllib.request.urlopen(_request(release.setup_url), timeout=60) as response:
            total = int(response.headers.get("Content-Length") or release.size or 0)
            with partial.open("wb") as handle:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if progress is not None:
                        progress(done, total)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        partial.unlink(missing_ok=True)
        raise UpdateError("Le téléchargement de la mise à jour a échoué.") from exc

    if total and done != total:
        partial.unlink(missing_ok=True)
        raise UpdateError("Le téléchargement est incomplet. Réessaie.")

    actual = digest.hexdigest()
    if not hmac.compare_digest(actual, expected):
        partial.unlink(missing_ok=True)
        raise UpdateError(
            "L’intégrité de l’installateur téléchargé est invalide. "
            "La mise à jour a été annulée."
        )
    os.replace(partial, target)
    return target


def launch_installer(path: Path, silent: bool = True,
                     install_dir: Path | None = None) -> subprocess.Popen:
    """Démarre l'installateur détaché, sans fenêtre de console."""
    args = [str(path)]
    if silent:
        args.append("/S")
    if install_dir is not None:
        args.append(f"/DIR={install_dir}")
    flags = 0
    flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.Popen(args, cwd=str(Path(path).parent), close_fds=True,
                            creationflags=flags)


def cleanup_download_cache(keep: Path | None = None) -> None:
    """Supprime les anciens installateurs téléchargés (jamais le coffre)."""
    base = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "NoctisAuth" / "Updates"
    if not base.is_dir():
        return
    for item in base.iterdir():
        try:
            if keep is not None and item.resolve() == keep.resolve():
                continue
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
        except OSError:
            pass
