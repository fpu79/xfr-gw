# xfr-gw

Das Gateway holt freigegebene Transfers vom `xfr-core` ab, speichert sie lokal und stellt sie dem Benutzer per Webserver bereit.

## MVP-Ablauf

1. `python manage.py pull_transfers` fragt den Core nach freigegebenen Transfers.
2. Neue Dateien werden in `storage/` gespeichert.
3. Die Startseite zeigt die vorhandenen Dateien als Downloadlinks an.

Das Abholen kann zunächst regelmäßig per systemd-Timer oder Cron gestartet werden. Eine Queue oder Celery ist für den MVP nicht nötig.

## Erwartete Core-Antwort

```json
[
  {
    "id": 12,
    "filename": "bericht.pdf",
    "download_url": "/api/gateway/transfers/12/download/",
    "expires_at": "2026-09-04T12:00:00Z"
  }
]
```

## Lokaler Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py runserver
```

Konfiguration erfolgt über Umgebungsvariablen:

- `XFR_CORE_READY_URL`: URL der Transferliste
- `XFR_CORE_TOKEN`: Bearer-Token für den Core
- `XFR_STORAGE_DIR`: lokale Dateiablage
- `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_DEBUG`: Django-Basiskonfiguration

## Bewusst noch nicht enthalten

- Benutzeranmeldung und Rollen
- automatische Löschung abgelaufener Dateien
- Rückmeldung an den Core nach erfolgreicher Abholung
- produktiver WSGI-Webserver und systemd-Units
