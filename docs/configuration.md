# Konfiguration

Alle Einstellungen werden über Umgebungsvariablen mit Präfix `IDM_` oder eine
`.env`-Datei bereitgestellt. Die Registerkarte selbst stammt aus
[idm-heatpump-api](https://github.com/Xerolux/idm-heatpump-api) – eine eigene
Registerdatei ist nicht mehr nötig.

## Verbindung

| Variable | Standard | Bedeutung |
|---|---:|---|
| `IDM_HOST` | leer | IP-Adresse/Hostname; erforderlich |
| `IDM_PORT` | `502` | Modbus-TCP-Port |
| `IDM_SLAVE_ID` | `1` | Modbus Slave-ID |
| `IDM_TIMEOUT` | `10.0` | Timeout in Sekunden |
| `IDM_MAX_RETRIES` | `3` | Wiederholungen pro Modbus-Kommando |

## Modell und Anlagenstruktur

| Variable | Standard | Bedeutung |
|---|---:|---|
| `IDM_MODEL` | leer | Leer = automatische Erkennung über `detect_model`. Alternativ Alias: `navigator10`, `navigator20`, `navigatorpro`, `navigator17` |
| `IDM_HEATING_CIRCUITS` | leer | Nur bei manuellem Modell: aktive Heizkreise, z. B. `A,B` (Standard `A`) |
| `IDM_ZONE_MODULES` | leer | Nur bei manuellem Modell: Anzahl Zonenmodule (0–10) |
| `IDM_ROOMS_PER_ZONE` | `6` | Räume je Zonenmodul (6 oder 8) |

Die automatische Erkennung ermittelt Controller-Familie (Navigator 1.7 / 2.0 /
10 / Pro), aktive Heizkreise, Zonenmodule, Solar, ISC, PV und Kaskade und baut
daraus die passende Registerkarte (typischerweise 100–600 Datenpunkte).

## Schreibschutz

Ein Schreibzugriff wird nur ausgeführt, wenn **alle** Bedingungen erfüllt sind:

1. `IDM_ALLOW_WRITES=true` aktiviert Schreiben global,
2. die Write-Klasse des Registers steht in `IDM_WRITE_CLASSES`
   (`volatile`, `cyclic`, `eeprom`, `write_only` – kommagetrennt),
3. ist `IDM_WRITABLE_KEYS` gesetzt, muss der Registernamen (z. B.
   `dhw_setpoint`) darin enthalten sein.

Darin liegen die Write-Klassen:

| Klasse | Bedeutung | Typische Register |
|---|---|---|
| `volatile` | flüchtig, jederzeit sicher schreibbar | RAM-Sollwerte, GLT-Anforderungen |
| `cyclic` | muss zyklisch erneuert werden (sonst verwirft sie der Controller) | `glt_temp_demand_heating` u. ä. |
| `eeprom` | dauerhaft, verschleißbehaftet – API drosselt auf 1 Schreibzugriff/60 s | `system_mode`, `dhw_setpoint`, Heizkurven |
| `write_only` | nur Trigger, nicht lesbar | `error_acknowledge` |

Darüber hinaus validiert `idm-heatpump-api` bei jedem Schreibzugriff Wertebereich,
Enums, Modellverfügbarkeit und verweigert unzulässige Werte – unabhängig von der
Konfiguration hier. Mit `validate_write` bzw. `dry_run=true` kann jeder
Schreibplan vorab geprüft werden, ohne das Gerät zu berühren.

## Sonstiges

| Variable | Standard | Bedeutung |
|---|---:|---|
| `IDM_CACHE_TTL` | `5` | Sekunden, die ein `read_all`-Snapshot gilt (`0` = deaktiviert) |
