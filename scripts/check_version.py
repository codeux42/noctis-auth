"""Vérifie que le tag Git, VERSION et app_config.py sont alignés."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

import app_config  # noqa: E402


def main() -> int:
    errors = []
    version_file = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version_file):
        errors.append(f'VERSION invalide : {version_file!r}')
    if app_config.APP_VERSION != version_file:
        errors.append(
            f'app_config.APP_VERSION ({app_config.APP_VERSION}) != VERSION ({version_file})')
    ref = os.getenv('GITHUB_REF_NAME', '').strip()
    if ref.startswith('v') and re.fullmatch(r'v\d+\.\d+\.\d+', ref):
        tag_version = ref[1:]
        if tag_version != version_file:
            errors.append(f'Le tag {ref} ne correspond pas à VERSION ({version_file})')
    if app_config.SETUP_EXE != 'NoctisAuth_Setup.exe':
        errors.append('SETUP_EXE doit rester NoctisAuth_Setup.exe')
    if app_config.APP_EXE != 'NoctisAuth.exe':
        errors.append('APP_EXE doit rester NoctisAuth.exe')
    if errors:
        for error in errors:
            print(f'ERREUR : {error}', file=sys.stderr)
        return 1
    print(f'Version validée : {version_file} (tag={ref or "local"})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
