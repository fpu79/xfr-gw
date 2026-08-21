from pathlib import Path
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from .models import Transfer


def _headers():
    return {"Authorization": f"Bearer {settings.XFR_CORE_TOKEN}"} if settings.XFR_CORE_TOKEN else {}


def fetch_ready_transfers():
    response = requests.get(settings.XFR_CORE_READY_URL, headers=_headers(), timeout=30)
    response.raise_for_status()

    storage = Path(settings.XFR_STORAGE_DIR)
    storage.mkdir(parents=True, exist_ok=True)
    created = 0

    for item in response.json():
        external_id = str(item["id"])
        if Transfer.objects.filter(external_id=external_id).exists():
            continue

        filename = Path(item["filename"]).name
        download_url = urljoin(settings.XFR_CORE_READY_URL, item["download_url"])
        target = storage / f"{external_id}_{filename}"

        with requests.get(download_url, headers=_headers(), timeout=300, stream=True) as download:
            download.raise_for_status()
            with target.open("wb") as output:
                for chunk in download.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)

        Transfer.objects.create(
            external_id=external_id,
            filename=filename,
            local_path=str(target),
            expires_at=parse_datetime(item.get("expires_at") or ""),
        )
        created += 1

    return created
