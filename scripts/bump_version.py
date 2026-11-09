"""Met à jour la version dans VERSION, app_config.py et la documentation.

Exemple :
    py scripts/bump_version.py 2.9.1
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r'\d+\.\d+\.\d+')


def main(argv: list[str]) -> int:
    if len(argv) != 1 or not PATTERN.fullmatch(argv[0]):
        print('Usage : py scripts/bump_version.py X.Y.Z', file=sys.stderr)
        return 2
    version = argv[0]

    (ROOT / 'VERSION').write_text(version + '\n', encoding='utf-8')

    config = ROOT / 'src' / 'app_config.py'
    text = config.read_text(encoding='utf-8')
    updated, count = re.subn(r'(?m)^APP_VERSION = "\d+\.\d+\.\d+"$',
                             f'APP_VERSION = "{version}"', text)
    if count != 1:
        print('APP_VERSION introuvable dans src/app_config.py', file=sys.stderr)
        return 1
    config.write_text(updated, encoding='utf-8')

    notes = ROOT / 'docs' / 'LISEZ-MOI.txt'
    if notes.is_file():
        content = notes.read_text(encoding='utf-8')
        content = re.sub(r'(?m)^NOCTIS AUTH \d+\.\d+\.\d+$',
                         f'NOCTIS AUTH {version}', content, count=1)
        notes.write_text(content, encoding='utf-8')

    print(f'Version mise à jour : {version}')
    print('Prochaines étapes :')
    print('  1. compléter CHANGELOG.md ;')
    print(f'  2. git add -A && git commit -m "Release v{version}" ;')
    print(f'  3. git tag v{version} && git push origin main --tags')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
