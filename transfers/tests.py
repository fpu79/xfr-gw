from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from .core_client import fetch_ready_transfers
from .models import Transfer


class GatewayTests(TestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health/").json(), {"status": "ok"})

    def test_empty_list(self):
        self.assertContains(self.client.get("/"), "keine Dateien")

    @patch("transfers.core_client.requests.get")
    def test_fetches_transfer_once(self, get):
        listing = Mock()
        listing.json.return_value = [{"id": 12, "filename": "../test.txt", "download_url": "/files/12", "expires_at": None}]
        listing.raise_for_status.return_value = None

        download = Mock()
        download.__enter__ = Mock(return_value=download)
        download.__exit__ = Mock(return_value=False)
        download.iter_content.return_value = [b"hello"]
        download.raise_for_status.return_value = None
        get.side_effect = [listing, download]

        with TemporaryDirectory() as directory, override_settings(XFR_STORAGE_DIR=Path(directory)):
            self.assertEqual(fetch_ready_transfers(), 1)
            self.assertEqual(Transfer.objects.get().filename, "test.txt")
            self.assertEqual(Path(Transfer.objects.get().local_path).read_bytes(), b"hello")
