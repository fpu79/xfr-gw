#!/usr/bin/env python3
import hashlib
import json
import os
import secrets
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


CORE_GATEWAY_URL = os.environ.get(
    "XFR_CORE_GATEWAY_URL",
    "http://127.0.0.1:8001/api/v1/gateway/transfers/",
).rstrip("/")
GATEWAY_TOKEN = os.environ.get("XFR_GATEWAY_TOKEN", "")
DOWNLOAD_ROOT = Path(
    os.environ.get("XFR_DOWNLOAD_ROOT", "/srv/xfr-gw/downloads")
)
PUBLIC_BASE_URL = os.environ.get(
    "XFR_PUBLIC_BASE_URL",
    "http://127.0.0.1:8080",
).rstrip("/")
RETENTION_DAYS = int(os.environ.get("XFR_RETENTION_DAYS", "14"))
TIMEOUT_SECONDS = int(os.environ.get("XFR_GATEWAY_TIMEOUT", "300"))
CHUNK_SIZE = 1024 * 1024


class GatewayError(Exception):
    pass


def api_request(url, method="GET", payload=None):
    if not GATEWAY_TOKEN:
        raise GatewayError("XFR_GATEWAY_TOKEN is not set")

    body = None
    headers = {
        "Authorization": f"Bearer {GATEWAY_TOKEN}",
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            response_body = response.read().decode("utf-8")
            return json.loads(response_body) if response_body else None
    except HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        raise GatewayError(
            f"Core returned HTTP {exc.code}: {response_body}"
        ) from exc
    except URLError as exc:
        raise GatewayError(f"Core is not reachable: {exc.reason}") from exc


def safe_filename(value):
    filename = Path(str(value)).name
    if filename in ("", ".", ".."):
        return "download.bin"
    return filename


def download_transfer(transfer, target):
    request = Request(
        transfer["download_url"],
        headers={"Authorization": f"Bearer {GATEWAY_TOKEN}"},
    )
    digest = hashlib.sha256()
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            with target.open("wb") as handle:
                while chunk := response.read(CHUNK_SIZE):
                    handle.write(chunk)
                    digest.update(chunk)
    except (HTTPError, URLError) as exc:
        target.unlink(missing_ok=True)
        raise GatewayError(f"Download failed: {exc}") from exc

    actual_checksum = digest.hexdigest()
    expected_checksum = str(transfer["checksum_sha256"]).lower()
    if actual_checksum != expected_checksum:
        target.unlink(missing_ok=True)
        raise GatewayError(
            f"Checksum mismatch: expected {expected_checksum}, "
            f"received {actual_checksum}"
        )


def write_metadata(directory, transfer_id, expires_at, download_url):
    metadata = {
        "transfer_id": str(transfer_id),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat(),
        "download_url": download_url,
    }
    temporary = directory / "metadata.json.tmp"
    final = directory / "metadata.json"
    temporary.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, final)


def publish_transfer(transfer):
    transfer_id = str(transfer["id"])
    filename = safe_filename(transfer["original_filename"])
    public_id = secrets.token_urlsafe(24)
    target_directory = DOWNLOAD_ROOT / public_id
    target_directory.mkdir(parents=True)
    temporary_file = target_directory / (filename + ".part")
    final_file = target_directory / filename

    try:
        download_transfer(transfer, temporary_file)
        os.replace(temporary_file, final_file)

        expires_at = datetime.now(timezone.utc) + timedelta(
            days=RETENTION_DAYS
        )
        download_url = (
            f"{PUBLIC_BASE_URL}/{quote(public_id)}/{quote(filename)}"
        )
        write_metadata(
            target_directory,
            transfer_id,
            expires_at,
            download_url,
        )

        confirmation_url = f"{CORE_GATEWAY_URL}/{transfer_id}/confirm/"
        api_request(
            confirmation_url,
            method="POST",
            payload={
                "checksum_sha256": transfer["checksum_sha256"],
                "download_url": download_url,
                "expires_at": expires_at.isoformat(),
            },
        )
        print(f"OK {transfer_id}: {download_url}")
        return True
    except Exception:
        # Keep a completely published directory if confirmation may have
        # reached the Core. Cleanup will remove it at expires_at.
        if not final_file.exists():
            shutil.rmtree(target_directory, ignore_errors=True)
        raise


def parse_datetime(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def cleanup_expired():
    if not DOWNLOAD_ROOT.exists():
        return 0

    removed = 0
    now = datetime.now(timezone.utc)
    for directory in DOWNLOAD_ROOT.iterdir():
        if not directory.is_dir():
            continue

        metadata_path = directory / "metadata.json"
        if not metadata_path.is_file():
            continue

        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            expires_at = parse_datetime(metadata["expires_at"])
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            print(
                f"WARNING {directory.name}: invalid metadata: {exc}",
                file=sys.stderr,
            )
            continue

        if expires_at <= now:
            shutil.rmtree(directory)
            removed += 1
            print(f"REMOVED {directory.name}: expired")

    return removed


def main():
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    removed = cleanup_expired()

    transfers = api_request(CORE_GATEWAY_URL)
    if not isinstance(transfers, list):
        raise GatewayError("Core returned an invalid transfer list")

    succeeded = 0
    failed = 0
    for transfer in transfers:
        try:
            print(
                f"FETCH {transfer.get('id', 'unknown')}: "
                f"{transfer.get('original_filename', 'unknown')}"
            )
            if publish_transfer(transfer):
                succeeded += 1
        except Exception as exc:
            failed += 1
            print(
                f"ERROR {transfer.get('id', 'unknown')}: {exc}",
                file=sys.stderr,
            )

    print(
        f"Finished: {succeeded} published, {failed} failed, "
        f"{removed} expired removed."
    )
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GatewayError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
