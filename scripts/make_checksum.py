"""Génère les empreintes SHA-256 des fichiers de dist/ pour les Releases."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> int:
    DIST.mkdir(exist_ok=True)
    found = []
    for name in ('NoctisAuth.exe', 'NoctisAuth_Setup.exe'):
        path = DIST / name
        if not path.is_file():
            continue
        value = digest(path)
        checksum = Path(str(path) + '.sha256')
        checksum.write_text(f'{value}  {path.name}\n', encoding='ascii')
        found.append((path, value, checksum))
        print(f'{path.name}: {value}')
    if not found:
        print('Aucun fichier à certifier dans dist/.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
