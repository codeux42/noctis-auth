"""Renseigne le dépôt GitHub utilisé par le système de mises à jour.

Exemples :
    py scripts/configure_repo.py --owner mon-compte --repo noctis-auth
    py scripts/configure_repo.py --from-environment

Le workflow GitHub Actions appelle automatiquement la seconde forme : le
propriétaire et le nom du dépôt sont alors ceux du dépôt qui compile.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / 'src' / 'app_config.py'
VALID = re.compile(r'[A-Za-z0-9_.-]+')


def update(owner: str, repo: str) -> None:
    text = CONFIG.read_text(encoding='utf-8')
    text, owner_count = re.subn(r'(?m)^GITHUB_OWNER = ".*"$',
                                f'GITHUB_OWNER = "{owner}"', text)
    text, repo_count = re.subn(r'(?m)^GITHUB_REPO = ".*"$',
                               f'GITHUB_REPO = "{repo}"', text)
    if owner_count != 1 or repo_count != 1:
        raise SystemExit('GITHUB_OWNER / GITHUB_REPO introuvables dans app_config.py')
    CONFIG.write_text(text, encoding='utf-8')
    for path in (ROOT / 'README.md', ROOT / 'CHANGELOG.md'):
        if not path.is_file():
            continue
        content = path.read_text(encoding='utf-8')
        if 'OWNER/REPO' not in content:
            continue
        path.write_text(content.replace('OWNER/REPO', f'{owner}/{repo}'),
                        encoding='utf-8')
        print(f'Liens GitHub mis à jour dans {path.name}')
    print(f'Dépôt de mises à jour configuré : {owner}/{repo}')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner')
    parser.add_argument('--repo')
    parser.add_argument('--from-environment', action='store_true',
                        help='lit GITHUB_REPOSITORY (format owner/repo)')
    args = parser.parse_args()
    owner, repo = args.owner, args.repo
    if args.from_environment:
        value = os.getenv('GITHUB_REPOSITORY', '')
        if '/' not in value:
            print('GITHUB_REPOSITORY est absent ou invalide.', file=sys.stderr)
            return 1
        owner, repo = value.split('/', 1)
    if not owner or not repo:
        parser.error('--owner et --repo sont requis (ou --from-environment)')
    if not VALID.fullmatch(owner) or not VALID.fullmatch(repo):
        print('Nom de compte ou de dépôt GitHub invalide.', file=sys.stderr)
        return 1
    update(owner, repo)
    return 0


if __name__ == '__main__':
    sys.exit(main())
