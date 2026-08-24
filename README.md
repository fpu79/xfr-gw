# xfr-gw

Das Gateway holt freigegebene Transfers vom XFR-Core ab, prüft die
SHA-256-Prüfsumme und stellt sie in einem nicht erratbaren Downloadpfad
bereit. Anschließend meldet es URL und tatsächlichen Ablaufzeitpunkt an
den Core zurück.

Der MVP besteht aus einem Python-Skript und benötigt keine zusätzlichen
Python-Pakete.

## Ablauf

```text
Core RELEASED
→ Gateway lädt Datei
→ SHA-256 prüfen
→ zufälligen Downloadpfad anlegen
→ expires_at festlegen
→ URL und expires_at an Core melden
→ Core setzt AVAILABLE
```

Bei jedem Lauf löscht das Skript außerdem Downloadordner, deren
`expires_at` erreicht ist. Damit ist das Gateway für die tatsächliche
Aufbewahrungsfrist verantwortlich.

## Konfiguration

| Variable | Standard | Zweck |
|---|---|---|
| `XFR_CORE_GATEWAY_URL` | `http://127.0.0.1:8001/api/v1/gateway/transfers/` | Gateway-API des Core |
| `XFR_GATEWAY_TOKEN` | keiner | Bearer-Token für die Gateway-API |
| `XFR_DOWNLOAD_ROOT` | `/srv/xfr-gw/downloads` | vom Webserver ausgelieferter Ordner |
| `XFR_PUBLIC_BASE_URL` | `http://127.0.0.1:8080` | öffentliche Basis-URL |
| `XFR_RETENTION_DAYS` | `14` | Aufbewahrung ab Bereitstellung |
| `XFR_GATEWAY_TIMEOUT` | `300` | HTTP-Timeout in Sekunden |

## Lokal testen

Voraussetzung ist ein Transfer im Core mit Status `RELEASED`.

Core mit Gateway-Token starten:

```bash
export STFS_GATEWAY_KIS1_TOKEN="gateway-test-token"
python manage.py runserver 0.0.0.0:8001
```

Gateway herunterladen und Branch auswählen:

```bash
git clone https://github.com/fpu79/xfr-gw.git
cd xfr-gw
git switch feature/gateway-mvp
```

Lokalen Downloadordner und Variablen setzen:

```bash
mkdir -p ./downloads

export XFR_CORE_GATEWAY_URL="http://127.0.0.1:8001/api/v1/gateway/transfers/"
export XFR_GATEWAY_TOKEN="gateway-test-token"
export XFR_DOWNLOAD_ROOT="$PWD/downloads"
export XFR_PUBLIC_BASE_URL="http://127.0.0.1:8080"
```

In einem zweiten Terminal den Downloadordner nur für den lokalen Test
ausliefern:

```bash
python -m http.server 8080 --directory ./downloads
```

Dann das Gateway einmal ausführen:

```bash
python gateway.py
```

Erwartete Ausgabe:

```text
FETCH <transfer-id>: datei.pdf
OK <transfer-id>: http://127.0.0.1:8080/<zufälliger-pfad>/datei.pdf
Finished: 1 published, 0 failed, 0 expired removed.
```

Der Core zeigt anschließend `AVAILABLE`, die konkrete URL sowie das
vom Gateway übermittelte `expires_at`.

## Späterer Betrieb

Später kann nginx `XFR_DOWNLOAD_ROOT` ausliefern und `gateway.py`
über einen systemd-Timer oder Cron regelmäßig gestartet werden. Token
und Konfiguration gehören dann in eine nur für das Dienstkonto lesbare
Umgebungsdatei.

Der Python-Testwebserver ist nicht für den produktiven Betrieb gedacht.
