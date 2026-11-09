"""Test isolé de l'installation silencieuse.

Le test n'écrit ni dans le vrai dossier utilisateur, ni dans le registre,
ni sur le Bureau : les fonctions Windows sont remplacées par des espions.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

import installer  # noqa: E402


class SilentInstallTests(unittest.TestCase):
    def test_install_copies_payload_and_preserves_data(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            payload = base / 'payload' / installer.APP_EXE
            payload.parent.mkdir(parents=True)
            payload.write_bytes(b'noctis-app' * 2048)
            icon = base / 'payload' / 'noctis.ico'
            icon.write_bytes(b'icon')

            install_dir = base / 'Programs' / 'Noctis Auth'
            desktop = base / 'Desktop'
            programs = base / 'Start Menu'
            desktop.mkdir()
            programs.mkdir()

            vault_dir = base / 'Roaming' / 'NoctisAuth'
            vault_dir.mkdir(parents=True)
            vault = vault_dir / 'vault.json'
            vault.write_bytes(b'encrypted-vault')

            shortcuts = []
            registered = {}

            def fake_resource(name):
                return str(base / 'payload' / Path(name).name)

            def fake_shortcuts(items):
                shortcuts.extend(items)

            def fake_register(target, setup):
                registered['target'] = Path(target)
                registered['setup'] = Path(setup)

            with mock.patch.object(installer, 'resource_path', side_effect=fake_resource), \
                    mock.patch.object(installer, 'desktop_folder', return_value=desktop), \
                    mock.patch.object(installer, 'programs_folder', return_value=programs), \
                    mock.patch.object(installer, 'create_shortcuts', side_effect=fake_shortcuts), \
                    mock.patch.object(installer, 'register_install', side_effect=fake_register):
                installer.silent_install(install_dir)

            self.assertEqual((install_dir / installer.APP_EXE).read_bytes(),
                             payload.read_bytes())
            self.assertTrue((install_dir / installer.SETUP_EXE).is_file())
            self.assertTrue((install_dir / 'noctis.ico').is_file())
            install_dir = install_dir.resolve()
            self.assertEqual(registered['target'], install_dir)
            self.assertEqual(registered['setup'], install_dir / installer.SETUP_EXE)
            names = {Path(item[0]).name for item in shortcuts}
            self.assertIn('Noctis Auth.lnk', names)
            self.assertIn('Désinstaller Noctis Auth.lnk', names)
            self.assertEqual(len(shortcuts), 3)
            self.assertEqual(vault.read_bytes(), b'encrypted-vault')

    def test_uninstall_arguments_keep_vault_by_default(self):
        options = installer.parse_args(['--uninstall'])
        self.assertTrue(options['uninstall'])
        self.assertFalse(options['purge'])
        options = installer.parse_args(['--uninstall', '/PURGE'])
        self.assertTrue(options['purge'])


if __name__ == '__main__':
    unittest.main()
