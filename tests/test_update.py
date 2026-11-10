"""Tests non graphiques : versions, intégrité SHA-256, ressources, installateur."""

from __future__ import annotations

import functools
import hashlib
import http.server
import socketserver
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

import app_config  # noqa: E402
import installer  # noqa: E402
import noctis_auth  # noqa: E402
import noctis_update  # noqa: E402


class VersionTests(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(noctis_update.parse_version('v2.9.1'), (2, 9, 1, 0))
        self.assertEqual(noctis_update.parse_version('2.10.0'), (2, 10, 0, 0))
        self.assertEqual(noctis_update.parse_version('inconnu'), (0, 0, 0, 0))

    def test_comparison(self):
        self.assertTrue(noctis_update.is_newer('2.9.1', '2.9.0'))
        self.assertTrue(noctis_update.is_newer('2.10.0', '2.9.9'))
        self.assertFalse(noctis_update.is_newer('2.9.0', '2.9.0'))
        self.assertFalse(noctis_update.is_newer('2.8.9', '2.9.0'))

    def test_version_sources_aligned(self):
        version_file = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
        self.assertEqual(version_file, app_config.APP_VERSION)
        self.assertEqual(app_config.SETUP_EXE, 'NoctisAuth_Setup.exe')

    def test_sha_parser(self):
        value = 'a' * 64
        self.assertEqual(noctis_update._parse_sha256(f'{value}  setup.exe'), value)
        with self.assertRaises(noctis_update.UpdateError):
            noctis_update._parse_sha256('pas une empreinte')


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class UpdateDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        payload = b'NoctisAuth-installer-test-' * 4096
        self.setup_name = 'NoctisAuth_Setup.exe'
        (self.folder / self.setup_name).write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        (self.folder / (self.setup_name + '.sha256')).write_text(
            f'{digest}  {self.setup_name}\n', encoding='ascii')
        handler = functools.partial(_QuietHandler, directory=str(self.folder))
        self.server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}'
        self.payload = payload

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def _release(self):
        return noctis_update.ReleaseInfo(
            version='2.9.1', tag='v2.9.1', name='Test', notes='',
            page_url=self.base, published_at='',
            setup_url=f'{self.base}/{self.setup_name}',
            setup_name=self.setup_name,
            sha256_url=f'{self.base}/{self.setup_name}.sha256',
            size=len(self.payload))

    def test_download_and_verify(self):
        seen = []
        output = Path(self.temp.name) / 'out'
        result = noctis_update.download_and_verify(
            self._release(), dest_dir=output,
            progress=lambda done, total: seen.append((done, total)))
        self.assertTrue(result.is_file())
        self.assertEqual(result.read_bytes(), self.payload)
        self.assertTrue(seen)
        self.assertEqual(seen[-1][0], len(self.payload))

    def test_corrupted_checksum_is_rejected(self):
        (self.folder / (self.setup_name + '.sha256')).write_text(
            'b' * 64 + f'  {self.setup_name}\n', encoding='ascii')
        output = Path(self.temp.name) / 'bad'
        with self.assertRaises(noctis_update.UpdateError):
            noctis_update.download_and_verify(self._release(), dest_dir=output)
        self.assertFalse((output / self.setup_name).exists())


class ApplicationTests(unittest.TestCase):
    def test_totp_service_catalog(self):
        self.assertEqual(len(noctis_auth.SERVICES), 34)
        names = {s['name'] for s in noctis_auth.SERVICES}
        self.assertEqual(len(names), len(noctis_auth.SERVICES))
        self.assertIn('Discord', names)
        self.assertIn('Google', names)
        self.assertIn('Autre', names)
        self.assertNotIn('Netflix', names)
        self.assertNotIn('Spotify', names)

    def test_base32_totp_secret(self):
        self.assertEqual(noctis_auth.totp('JBSWY3DPEHPK3PXP', timestamp=0), '282760')
        with self.assertRaises(Exception):
            noctis_auth.b32decode('CLE-INVENTEE')

    def test_assets_found(self):
        for name in ('assets/noctis_logo.png', 'assets/noctis_background.png',
                     'assets/discord.png', 'noctis.ico'):
            self.assertTrue(Path(noctis_auth.resource_path(name)).is_file(), name)

    def test_update_icon_exists(self):
        self.assertIsNotNone(noctis_auth.icon_pil('download', 24))


class InstallerTests(unittest.TestCase):
    def test_arguments(self):
        options = installer.parse_args(['/S', '/DIR=C:\\Jeux\\Noctis'])
        self.assertTrue(options['silent'])
        self.assertEqual(str(options['dir']), 'C:\\Jeux\\Noctis')
        options = installer.parse_args(['--uninstall', '/PURGE'])
        self.assertTrue(options['uninstall'])
        self.assertTrue(options['purge'])
        options = installer.parse_args(['--dir', 'D:\\Apps\\Noctis'])
        self.assertEqual(str(options['dir']), 'D:\\Apps\\Noctis')

    def test_glass_rendering(self):
        image = installer.render_glass(240, 48, 14, 'Installer', 'download',
                                       'gold', 'normal', installer.CARD)
        self.assertEqual(image.size, (240, 48))

    def test_atomic_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.bin'
            source.write_bytes(b'x' * 4096)
            destination = Path(folder) / 'destination.bin'
            installer._copy_with_retry(source, destination)
            self.assertEqual(destination.read_bytes(), source.read_bytes())

    def test_unconfigured_repository_is_safe(self):
        # Aucun appel réseau ne doit être tenté sans dépôt configuré.
        if not app_config.github_configured():
            self.assertIsNone(noctis_update.fetch_latest_release())


if __name__ == '__main__':
    unittest.main()
