# Changelog

Alle nennenswerten Änderungen an diesem Projekt werden hier dokumentiert. Das
Format folgt [Keep a Changelog](https://keepachangelog.com/de/), die Versionierung
[SemVer](https://semver.org).

## [0.4.0] – 2026-11-09

### Hinzugefügt

- `read_datapoints(keys[])`: mehrere Datenpunkte in einem Batch lesen
- Web-Supplement erweitert: `read_web_heating_circuit` (Betriebsmodus,
  Raum-Sollwerte mit geräteseitigen Grenzen, Pumpe), `read_web_weather`
  (Controller-eigene Wettervorhersage), `read_web_energyflow` (Netz/PV/Haus)
- `web_save_heatingcircuit_parameter`: Heizkreis-Parameter übers Web-Interface
  schreiben (`HK<x>NN`-Schema, Write-Klasse `eeprom`)
- Optionaler statischer Bearer-Token für den HTTP-Transport (`IDM_HTTP_TOKEN`)
- CI (GitHub Actions): Test-Matrix Python 3.12–3.14, Ruff, Build-Artefakt
- Release-Pipeline: PyPI (Trusted Publishing) und Container-Image auf GHCR
- Dependabot, `CHANGELOG.md`, `AGENTS.md`

### Verifiziert

- Live-Test an einer echten Anlage (Navigator 10, Heizkreise A+D, Solar/ISC/PV):
  Modellerkennung in unter einer Sekunde, 167 Werte im Voll-Snapshot,
  diagnose-clean; ausschließlich lesend

## [0.3.0] – 2026-11-09

### Hinzugefügt

- Optionales Web-Supplement über die im Controller gesetzte Web-PIN
  (`IDM_WEB_PIN`): `read_web_data`, `read_web_notifications` (Störungen im
  Klartext), `web_set_system_mode`, `web_save_dhw_setpoint`,
  `web_acknowledge_notifications`, `web_set_datetime`; Resource `idm://web`.
  Web-Schreibaktionen laufen durch die Write-Klasse ihres Modbus-Äquivalents
- Hintergrund-Poller (`IDM_POLL_INTERVAL`): Snapshot-Aktualisierung mit
  `PollRateLimiter`/`AdaptiveBackoff`, hält zyklische GLT-Anforderungen vor
  Ablauf ihrer TTL am Leben
- HTTP-Transport (`IDM_TRANSPORT=http`, Streamable HTTP, Standard `127.0.0.1:8308`)

## [0.2.0] – 2026-11-09

### Geändert

- Kompletter Neuaufbau auf `idm-heatpump-api[pymodbus]` (≥ 2.16.1): volle
  Registerkarte (100–600 Datenpunkte), automatische Modellerkennung
  (Navigator 1.7/2.0/10/Pro), Batch-Reads mit Snapshot-Cache,
  dreistufig abgesicherte Schreibvorgänge (`IDM_ALLOW_WRITES` +
  `IDM_WRITE_CLASSES` + `IDM_WRITABLE_KEYS`), `validate_write` (Dry-Run),
  `explain_error_code` (2005 Meldungen), `get_diagnostics`

### Entfernt

- **Breaking:** handgepflegte `registers.json` samt `IDM_REGISTER_MAP`,
  `IDM_WRITABLE_ADDRESSES`; `IDM_UNIT_ID` → `IDM_SLAVE_ID`

## [0.1.0] – 2026-10-26

- Erste Version: lokaler stdio-MCP-Server mit JSON-Registerdatei, Einzelwert-
  Lese/Schreibzugriffen über rohes pymodbus
