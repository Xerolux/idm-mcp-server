# IDM Heat Pump MCP Server

Ein unabhängiger Model Context Protocol (MCP)-Server, der KI-Assistenten kontrollierten Zugriff auf
eine IDM-Wärmepumpe über Modbus TCP ermöglicht. Damit können kompatible MCP-Clients Anlagenwerte
abfragen, verständlich anzeigen und – nur nach ausdrücklicher Freigabe – ausgewählte Sollwerte
schreiben.

> [!IMPORTANT]
> Dieses Community-Projekt steht in **keiner Verbindung, Partnerschaft oder Beauftragung mit der
> iDM Energiesysteme GmbH** und wird von ihr nicht unterstützt oder zertifiziert. „IDM“/„iDM“ und
> Produktnamen sind Kennzeichen ihrer jeweiligen Inhaber. Dieses Projekt ist keine offizielle
> Bedienoberfläche und ersetzt weder Herstellerdokumentation noch Fachbetrieb. Siehe
> [DISCLAIMER.md](DISCLAIMER.md).

## Wofür ist das Projekt gedacht?

Eine Wärmepumpe spricht normalerweise kein MCP. KI-Clients wie Claude Desktop, Claude Code, Codex
oder unterstützte IDEs können deshalb nicht direkt mit ihr kommunizieren. Dieser Server bildet die
Brücke zwischen beiden Welten:

```text
MCP-Client / KI-Assistent
          │ lokales MCP über stdio
          ▼
    IDM Heat Pump MCP Server
          │ idm-heatpump-api (Modbus TCP im lokalen Netz)
          ▼
        IDM-Wärmepumpe
```

Der Server übersetzt sprechende Namen wie `outdoor_temp` oder `hc_a_flow_temp` in Modbus-Zugriffe,
dekodiert Werte inklusive Einheit, Enumeration und Skalierung und stellt sie als MCP-Tools und
MCP-Resources bereit. Die komplette Registerkarte (je nach Anlage 100–600 Datenpunkte) und die
automatische Modell-Erkennung stammen aus der Bibliothek
[idm-heatpump-api](https://github.com/Xerolux/idm-heatpump-api), die auch die Home-Assistant-
Integration [idm-heatpump-hass](https://github.com/Xerolux/idm-heatpump-hass) verwendet – beide
pflegen damit dieselbe, an realen Anlagen verifizierte Registerdatenbasis.

Typische Anwendungsfälle sind:

- aktuelle Betriebswerte in natürlicher Sprache abfragen („Wie warm ist der Puffer?“),
- einen vollständigen Anlagen-Snapshot mit einem Aufruf lesen (`read_all_datapoints`),
- einem KI-Assistenten die verfügbaren Werte samt Einheit, Grenzen und Write-Klasse zeigen,
- Diagnosegespräche mit aktuellen Anlagendaten und Fehlercode-Erklärungen unterstützen und
- nach bewusster, mehrstufiger Freigabe einzelne Sollwerte ändern – mit trockener Vorprüfung.

Der Server ist **kein dauerhaftes Monitoring-System**: Er speichert keine Messhistorie, erstellt
keine Diagramme und ersetzt weder Home Assistant noch `idm-heatpump-api` selbst.

## Was kann der Server?

- **Modell erkennen:** Controller-Familie (Navigator 1.7 / 2.0 / 10 / Pro), aktive Heizkreise,
  Zonenmodule, Solar, ISC, PV und Kaskade automatisch ermitteln.
- **Datenpunkte auflisten:** Schlüssel, Adresse, Datentyp, Einheit, Skalierung, Wertebereich,
  Enum-Optionen und Write-Klasse anzeigen.
- **Live-Werte lesen:** Einzelwerte oder alle lesbaren Datenpunkte in einem Batch (mit kurzem
  Snapshot-Cache) lesen.
- **Werte verstehen:** Enumerationen (z. B. Betriebsmodi) werden mit Label übersetzt,
  „nicht konfiguriert“-Sentinelwerte als `unused` markiert.
- **Fehlercodes erklären:** die 2005 Meldungsnummern der Controller-Datenbank mit Benutzer- und
  Servicetext auflösen.
- **Kontrolliert schreiben:** Schreibpläne ohne Gerätekontakt validieren (`validate_write`) und
  freigegebene Register mit voller Bereichs-, Enum- und Modellprüfung schreiben.
- **Diagnose:** Verbindungsstatus, dauerhaft fehlgeschlagene und nicht unterstützte Register sowie
  zyklische Schreibanforderungen einsehen.
- **Web-Supplement (optional):** über die im Controller gesetzte Web-PIN (`IDM_WEB_PIN`) stehen das
  Navigator-10-WebSocket- bzw. Navigator-2.0-HTTP-Interface bereit: aktive Störungen im Klartext,
  Softwarestand und Gerätebezeichnung lesen sowie Betriebsmodus, Warmwasser-Sollwert, Uhrzeit
  setzen und Meldungen quittieren. Web-Schreibaktionen laufen durch dieselbe Write-Klassen-Freigabe
  wie die äquivalenten Modbus-Register.
- **Hintergrund-Polling (optional):** mit `IDM_POLL_INTERVAL` aktualisiert ein Hintergrundtask den
  Snapshot, überwacht die Verbindung (Exponential-Backoff bei Störungen) und hält zyklische
  GLT-Anforderungen (`cyclic`-Register) vor Ablauf ihrer TTL am Leben.
- **Zwei Transporte:** lokales `stdio` (Standard) oder Streamable-HTTP (`IDM_TRANSPORT=http`,
  bindet standardmäßig an `127.0.0.1`) – etwa für Container- oder LAN-Betrieb hinter einem
  abgesicherten Reverse-Proxy. Ein optionaler statischer Bearer-Token (`IDM_HTTP_TOKEN`)
  schützt den HTTP-Endpunkt zusätzlich ab.
- **An realer Anlage verifiziert:** Modellerkennung (Navigator 10 mit Solar/ISC/PV und
  nicht zusammenhängenden Heizkreisen), Voll-Snapshot und Diagnose sind gegen eine echte
  Anlage getestet.
- **Lokal bleiben:** Die Verbindung zur Wärmepumpe erfolgt aus dem eigenen Netzwerk; der Server
  benötigt keinen Cloud-Zugang.

### Verfügbare MCP-Tools

| Tool | Zweck | Beispiel |
|---|---|---|
| `detect_model` | Controller-Modell und Anlagenstruktur erkennen | „Erkenne meine Wärmepumpe.“ |
| `list_datapoints` | Datenpunkte mit Metadaten anzeigen (filterbar) | „Welche Werte gibt es zum Warmwasser?“ |
| `read_datapoint` | Aktuellen Wert eines Datenpunkts lesen | „Lies `outdoor_temp` aus.“ |
| `read_datapoints` | Mehrere Datenpunkte in einem Batch lesen | „Lies Außentemp., Speicher und Vorlauf.“ |
| `read_all_datapoints` | Kompletten Anlagen-Snapshot lesen | „Gib mir alle aktuellen Werte.“ |
| `validate_write` | Schreibplan prüfen, ohne zu schreiben | „Wäre 52 °C Warmwasser erlaubt?“ |
| `write_datapoint` | Freigegebenen Wert setzen (Default: gesperrt) | „Setze `dhw_setpoint` auf 52.“ |
| `explain_error_code` | Controller-Meldungsnummer erklären | „Was bedeutet Meldung 142?“ |
| `get_diagnostics` | Verbindungs- und Registerdiagnose | „Welche Register schlagen fehl?“ |
| `read_web_data` | Lokales Web-Interface auslesen (Softwarestand, Modell, Infosystem) | „Welche Firmware hat der Navigator?“ |
| `read_web_notifications` | Aktive Störungen mit Klartext (Navigator 10) | „Welche Meldungen liegen an?“ |
| `read_web_heating_circuit` | Heizkreis-Status mit geräteseitigen Grenzen | „Zeige Heizkreis A mit Sollwerten.“ |
| `read_web_weather` | Controller-eigene Wettervorhersage (myiDM) | „Was sagt die Vorhersage für morgen?“ |
| `read_web_energyflow` | Momentanleistungen Netz/PV/Haus | „Wie viel PV-Überschuss ist da?“ |
| `web_set_system_mode` | Betriebsmodus per Web setzen (0–5) | „Stelle auf Nur-Warmwasser.“ |
| `web_save_dhw_setpoint` | Warmwasser-Sollwert per Web setzen | „Setze Warmwasser auf 52 °C.“ |
| `web_save_heatingcircuit_parameter` | Heizkreis-Parameter per Web setzen (`HK<x>NN`) | „Raumsoll HK A auf 21,5 °C.“ |
| `web_acknowledge_notifications` | Störungen per Web quittieren | „Quittiere alle Meldungen.“ |
| `web_set_datetime` | Controller-Uhr stellen | „Synchronisiere die Uhr.“ |

### Verfügbare MCP-Resources

| Resource | Inhalt |
|---|---|
| `idm://model` | Erkanntes Modell und Fähigkeiten |
| `idm://datapoints` | Vollständige Datenpunkt-Karte |
| `idm://datapoints/{key}` | Aktueller Wert eines Datenpunkts |
| `idm://values` | Zwischengespeicherter Gesamt-Snapshot |
| `idm://diagnostics` | Client-Diagnose |
| `idm://web` | Web-Supplement-Snapshot (sofern verbunden) |

Welche konkreten Datenpunkte existieren, entscheidet die erkannte Anlage bzw. die Registerkarte
der `idm-heatpump-api`.

## Sicherheitskonzept

Der Server startet grundsätzlich **read-only**. Ein Schreibzugriff wird nur ausgeführt, wenn alle
drei Bedingungen gleichzeitig erfüllt sind:

1. `IDM_ALLOW_WRITES=true` aktiviert Schreiben global,
2. die Write-Klasse des Registers (`volatile`, `cyclic`, `eeprom` oder `write_only`) steht in
   `IDM_WRITE_CLASSES`, und
3. ist `IDM_WRITABLE_KEYS` gesetzt, enthält diese Allowlist den Registernamen.

Darüber hinaus validiert `idm-heatpump-api` jeden Schreibzugriff gegen Wertebereich, Enumerationen
und Modellverfügbarkeit und drosselt wiederholte EEPROM-Schreibzugriffe (max. einer pro Register
und 60 s) zum Schutz des begrenzt beschreibbaren Controllerspeichers. Mit `validate_write` oder
`dry_run=true` lässt sich jeder Schreibplan vorab prüfen, ohne das Gerät zu berühren. Weitere
Hinweise stehen unter [Sicherer Betrieb](docs/safety.md).

Web-Schreibaktionen werden über die Write-Klasse ihres jeweiligen Modbus-Äquivalents kontrolliert:
`web_set_system_mode` und `web_save_dhw_setpoint` benötigen `eeprom` (wie `system_mode` bzw.
`dhw_setpoint`), `web_acknowledge_notifications` benötigt `write_only` (wie `error_acknowledge`),
`web_set_datetime` benötigt `volatile`. Eine gesetzte `IDM_WRITABLE_KEYS`-Allowlist greift auch hier.

## Voraussetzungen

- IDM-Wärmepumpe mit aktiviertem und im LAN erreichbarem Modbus TCP
- Python 3.12 oder neuer oder alternativ Docker
- ein lokaler MCP-Client mit `stdio`-Unterstützung

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
cp .env.example .env
# .env an die eigene Anlage anpassen (mindestens IDM_HOST)
idm-mcp
```

Modell und Registerkarten werden beim ersten Aufruf von `detect_model` automatisch ermittelt;
eine eigene Registerdatei ist nicht erforderlich. Wer die Erkennung überspringen möchte, setzt
`IDM_MODEL` (z. B. `navigator10`).

Danach wird die gewünschte KI-Anwendung gemäß der
[clientbezogenen Anleitung](docs/clients.md) eingerichtet. Ein sinnvoller erster Test im Client ist:

> Erkenne meine Wärmepumpe und zeige mir danach alle verfügbaren Datenpunkte. Schreibe keine Werte.

Anschließend kann ein konkreter Messwert gelesen werden:

> Lies `outdoor_temp` und `storage_temp` und erkläre Wert und Einheit. Verändere nichts.

## MCP-Client

Eine ausführliche, clientbezogene Anleitung ist unter
**[Claude, ChatGPT, GitHub Copilot, Codex und Z.ai einrichten](docs/clients.md)** verfügbar.

Wichtig: Dieser Server verwendet aktuell den lokalen MCP-Transport `stdio`. Claude Desktop,
Claude Code, Codex CLI und unterstützte IDEs können ihn direkt als lokalen Prozess starten.
Webdienste wie ChatGPT im Browser oder GitHub.com können dagegen keinen Prozess auf dem eigenen
Rechner starten. Dafür wäre ein separat abgesicherter HTTPS-MCP-Gateway erforderlich; der
Modbus-Port der Wärmepumpe darf dafür keinesfalls ins Internet gestellt werden.

## Dokumentation / Wiki-Vorlage

- [Installation](docs/installation.md)
- [Konfiguration](docs/configuration.md)
- [Claude, ChatGPT, GitHub Copilot, Codex und Z.ai](docs/clients.md)
- [Sicherer Betrieb](docs/safety.md)
- [Haftungs- und Markenhinweis](DISCLAIMER.md)

Die Seiten unter `docs/` können in ein GitHub-Wiki übernommen werden. GitHub-Wikis liegen technisch
in einem separaten Repository und werden nicht automatisch mit diesem Repository veröffentlicht.

## Aktuelle Grenzen

- Lesen und Schreiben einzelner 16-/32-Bit-Register gemäß Registerkarte der
  `idm-heatpump-api`; keine freien Rohadressen ohne Kartenbezug,
- Web-Supplement nur gegen lokal erreichbares Web-Interface mit gesetzter PIN; Navigator 1.x hat
  kein lokales Web-Interface,
- keine mitgelieferte Zeitreihen, Statistiken, Diagramme oder lokale Datenbank (das
  Hintergrund-Polling hält nur den letzten Snapshot vor),
- HTTP-Transport ohne eigene Authentifizierung – nur an `127.0.0.1` binden oder vor einen
  Reverse-Proxy mit TLS und Zugangsbeschränkung setzen,
- keine Authentifizierung innerhalb von Modbus TCP.

Diese Einschränkungen sind bewusst sichtbar dokumentiert, damit der Server nicht mit Fähigkeiten
eingesetzt wird, die er derzeit nicht besitzt.

## Lizenz

Der Quellcode steht unter der [MIT-Lizenz](LICENSE). Sie erlaubt Nutzung, Änderung und Weitergabe
unter Beibehaltung des Lizenz- und Copyright-Hinweises und enthält einen Gewährleistungs- und
Haftungsausschluss. Der ergänzende [Disclaimer](DISCLAIMER.md) erklärt Projektstatus und Betriebsrisiken
in verständlicher Form; er ersetzt keine Rechtsberatung.
