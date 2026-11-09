"""Extrait les notes d'une version depuis CHANGELOG.md pour GitHub Releases."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def extract(version: str) -> str:
    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    pattern = re.compile(
        rf'(?ms)^##\s*\[?v?{re.escape(version)}\]?.*?$\n(.*?)(?=^##\s|\Z)')
    match = pattern.search(changelog)
    if not match:
        return (f'Noctis Auth {version}\n\n'
                'Installateur Windows autonome, sans Python requis.\n'
                'Le coffre chiffré et les comptes existants sont conservés.')
    body = match.group(1).strip()
    return body or f'Noctis Auth {version}'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    parser.add_argument('--output', default='release-notes.md')
    args = parser.parse_args()
    version = args.version.lstrip('vV')
    Path(args.output).write_text(extract(version) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
