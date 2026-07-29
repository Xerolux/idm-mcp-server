# IDM Heat Pump MCP Server

Ein unabhängiger Model Context Protocol (MCP)-Server, der KI-Assistenten kontrollierten Zugriff auf
eine IDM-Wärmepumpe über Modbus TCP ermöglicht. Damit können kompatible MCP-Clients konfigurierte
Anlagenwerte abfragen, verständlich anzeigen und – nur nach ausdrücklicher Freigabe – ausgewählte
Sollwerte schreiben.

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
          │ MCP über stdio oder HTTP
          ▼
   IDM Heat Pump MCP Server
          │ Modbus TCP im lokalen Netz
          ▼
       IDM-Wärmepumpe
```

Der Server verwendet dafür direkt die zentrale Bibliothek
[`idm-heatpump-api`](https://github.com/Xerolux/idm-heatpump-api), die auch das Home-Assistant-Projekt
[`idm-heatpump-hass`](https://github.com/Xerolux/idm-heatpump-hass) versorgt. Sie erkennt Modell und
installierte Komponenten, wählt die passende gepflegte Registerkarte, liest den Rohwert und
dekodiert Datentyp, Skalierung, Sentinel- und Enum-Werte. Dadurch dupliziert der MCP-Server weder die
Registerliste noch die anspruchsvolle Modbus- und Schreiblogik.

Typische Anwendungsfälle sind:

- aktuelle, konfigurierte Betriebswerte in natürlicher Sprache abfragen,
- Temperaturen oder andere einzelne Messwerte auslesen,
- einem KI-Assistenten die verfügbaren Werte samt Einheit und Beschreibung zeigen,
- Diagnosegespräche mit aktuellen Anlagendaten unterstützen und
- nach bewusster Freigabe einzelne, geprüfte Sollwerte innerhalb definierter Grenzen ändern.

Der Server ist **kein dauerhaftes Monitoring-System**: Er speichert keine Messhistorie und erstellt
keine Diagramme. Dafür bleibt Home Assistant die passende Oberfläche; MCP liefert Live-Daten und
Aktionen für KI-Assistenten.

## Was kann der Server?

- **Entities auflisten:** Namen, Adressen, Einheiten, Datentypen und Schreibregeln anzeigen.
- **Live-Werte lesen:** Ein konfiguriertes Holding- oder Input-Register direkt von der Wärmepumpe
  lesen.
- **Alle API-Datentypen dekodieren:** `FLOAT` (32 Bit/Word-Swap), `UCHAR`, `INT8`, `INT16`, `UINT16`,
  `BOOL` und `BITFLAG` inklusive Skalierung, Sentinel- und Enum-Werten.
- **Kontrolliert schreiben:** Ein freigegebenes Holding-Register skalieren, auf Minimal- und
  Maximalwert prüfen und schreiben.
- **Anlage automatisch erkennen:** Navigator 10, Navigator 2.0 bzw. Navigator Pro, Firmware,
  Heizkreise, Zonenmodule und optionale Anlagenfunktionen werden durch `idm-heatpump-api` erkannt.
- **Die zentrale Registerkarte verwenden:** System, Warmwasser, Heizkreise, Räume/Zonenmodule,
  Solar, PV, ISC und Kaskade stammen aus der gepflegten API statt aus Beispieldateien.
- **Mehrere Werte effizient lesen:** Zusammenhängende Register werden über den Batch-Reader der API
  gruppiert, mit Retry, Reconnect und sicherem Fallback auf Einzelabfragen.
- **Mehrere MCP-Oberflächen bedienen:** Funktionen werden sowohl als MCP-Tools als auch als
  MCP-Resources angeboten.
- **Lokal bleiben:** Die Verbindung zur Wärmepumpe erfolgt aus dem eigenen Netzwerk; der Server
  benötigt keinen Cloud-Zugang.

### Verfügbare MCP-Tools

| Tool | Zweck | Beispiel |
|---|---|---|
| `get_system_info` | Modell, Firmware, erkannte Komponenten und Diagnose anzeigen | „Welche IDM-Anlage wurde erkannt?“ |
| `list_entities` | Alle zum erkannten Modell passenden Entities anzeigen | „Welche Wärmepumpenwerte kannst du lesen?“ |
| `read_entity` | Aktuellen Wert eines Entity lesen | „Lies `outdoor_temp` aus.“ |
| `read_entities` | Mehrere Werte effizient in einer Batch-Abfrage lesen | „Lies Außen- und Speichertemperatur.“ |
| `write_entity` | Wert zunächst simulieren oder ausdrücklich erlaubt schreiben | „Prüfe den Sollwert 21 °C als Dry-Run.“ |

### Verfügbare MCP-Resources

| Resource | Inhalt |
|---|---|
| `idm://system` | Erkanntes Modell, Fähigkeiten und Modbus-Diagnose |
| `idm://entities` | Liste aller konfigurierten Entities |
| `idm://entities/{name}` | Aktueller Wert eines bestimmten Entity |

Welche Werte verfügbar sind, wird aus dem erkannten Modell und den erkannten Anlagenkomponenten mit
der Registerkarte aus `idm-heatpump-api` aufgebaut. `list_entities(writable_only=true)` filtert auf
die von der API fachlich als schreibbar markierten Register.

## Sicherheitskonzept

Der Server startet grundsätzlich **read-only**. Ein Schreibzugriff wird nur ausgeführt, wenn alle
drei Bedingungen gleichzeitig erfüllt sind:

1. `IDM_ALLOW_WRITES=true` aktiviert Schreiben global,
2. das betreffende Entity besitzt `"writable": true`, und
3. sein kanonischer API-Name steht zusätzlich in `IDM_WRITABLE_ENTITIES`.

`write_entity` ist darüber hinaus standardmäßig ein **Dry-Run**. Erst `dry_run=false` sendet nach
allen Prüfungen tatsächlich. Die API validiert Datentyp, Enum, Minimum/Maximum, Modellverfügbarkeit,
EEPROM-Schreibabstände sowie zyklische und schreibgeschützte Register. Weitere Hinweise stehen unter
[Sicherer Betrieb](docs/safety.md).

## Voraussetzungen

- IDM-Wärmepumpe mit aktiviertem und im LAN erreichbarem Modbus TCP
- Python 3.12 oder neuer oder alternativ Docker
- ein MCP-Client mit lokalem `stdio` oder Zugriff auf den optionalen HTTP-Endpunkt

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
cp .env.example .env
# IDM_HOST in .env anpassen
idm-mcp
```

Beim ersten Tool-Aufruf erkennt die Bibliothek die IDM-Generation und installierten Komponenten.
Mit `get_system_info` lässt sich das Ergebnis kontrollieren. Eine manuelle Registerdatei ist nicht
mehr notwendig.

Danach wird die gewünschte KI-Anwendung gemäß der
[clientbezogenen Anleitung](docs/clients.md) eingerichtet. Ein sinnvoller erster Test im Client ist:

> Liste alle konfigurierten IDM-Entities auf. Schreibe keine Werte.

Anschließend kann ein tatsächlich konfiguriertes Entity gelesen werden:

> Lies `outdoor_temp` und erkläre Wert und Einheit. Verändere nichts.

## MCP-Client

Eine ausführliche, clientbezogene Anleitung ist unter
**[Claude, ChatGPT, GitHub Copilot, Codex und Z.ai einrichten](docs/clients.md)** verfügbar.

Standard ist der lokale MCP-Transport `stdio`. Für Integrationen im vertrauenswürdigen Netz kann
der Server zusätzlich mit `idm-mcp --transport http` auf `http://127.0.0.1:8100/mcp` gestartet
werden. Der HTTP-Transport besitzt noch keine projektseitige Authentifizierung und bindet deshalb
standardmäßig nur an Loopback. Für Internetzugriff ist weiterhin ein abgesicherter Gateway nötig.

## Dokumentation / Wiki-Vorlage

- [Installation](docs/installation.md)
- [Konfiguration](docs/configuration.md)
- [Claude, ChatGPT, GitHub Copilot, Codex und Z.ai](docs/clients.md)
- [Sicherer Betrieb](docs/safety.md)
- [Haftungs- und Markenhinweis](DISCLAIMER.md)

Die Seiten unter `docs/` können in ein GitHub-Wiki übernommen werden. GitHub-Wikis liegen technisch
in einem separaten Repository und werden nicht automatisch mit diesem Repository veröffentlicht.

## Bewusste Grenzen

- MCP liefert Live-Zugriff; Historie, Statistiken, Diagramme und Datenbank übernimmt Home Assistant.
- HTTP ist für Loopback bzw. ein vertrauenswürdiges LAN vorgesehen und bringt derzeit keine eigene
  Benutzeranmeldung oder TLS-Terminierung mit.
- Modbus TCP selbst bietet keine Authentifizierung oder Verschlüsselung. Das lässt sich nicht im
  MCP-Layer reparieren; Wärmepumpe und MCP-Server müssen per Firewall/VLAN geschützt bleiben.
- Die Qualität der Modell- und Registererkennung folgt der verwendeten Version von
  `idm-heatpump-api`. Neue Erkenntnisse gehören zentral dorthin und werden danach automatisch für
  Home Assistant und MCP nutzbar.

## Lizenz

Der Quellcode steht unter der [MIT-Lizenz](LICENSE). Sie erlaubt Nutzung, Änderung und Weitergabe
unter Beibehaltung des Lizenz- und Copyright-Hinweises und enthält einen Gewährleistungs- und
Haftungsausschluss. Der ergänzende [Disclaimer](DISCLAIMER.md) erklärt Projektstatus und Betriebsrisiken
in verständlicher Form; er ersetzt keine Rechtsberatung.
