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
          │ lokales MCP über stdio
          ▼
   IDM Heat Pump MCP Server
          │ Modbus TCP im lokalen Netz
          ▼
       IDM-Wärmepumpe
```

Der Server übersetzt sprechende Namen wie `heating.outside_temperature` in die für das jeweilige
Gerät konfigurierte Modbus-Adresse, liest den Rohwert und rechnet ihn mit Datentyp, Skalierung,
Offset und Einheit in einen verständlichen Wert um. Dadurch muss der KI-Assistent weder
Registeradressen kennen noch selbst Binärwerte interpretieren.

Typische Anwendungsfälle sind:

- aktuelle, konfigurierte Betriebswerte in natürlicher Sprache abfragen,
- Temperaturen oder andere einzelne Messwerte auslesen,
- einem KI-Assistenten die verfügbaren Werte samt Einheit und Beschreibung zeigen,
- Diagnosegespräche mit aktuellen Anlagendaten unterstützen und
- nach bewusster Freigabe einzelne, geprüfte Sollwerte innerhalb definierter Grenzen ändern.

Der Server ist **kein dauerhaftes Monitoring-System**: Er speichert keine Messhistorie, erstellt
keine Diagramme und ersetzt weder Home Assistant noch `idm-heatpump-api`. Er stellt ausschließlich
die in der lokalen Registerdatei definierten Werte als MCP-Tools und MCP-Resources bereit.

## Was kann der Server?

- **Entities auflisten:** Namen, Adressen, Einheiten, Beschreibungen und Schreibregeln anzeigen.
- **Live-Werte lesen:** Ein konfiguriertes Holding- oder Input-Register direkt von der Wärmepumpe
  lesen.
- **Werte dekodieren:** Vorzeichenbehaftete `int16`- und vorzeichenlose `uint16`-Register inklusive
  Skalierung und Offset in verständliche Werte umrechnen.
- **Kontrolliert schreiben:** Ein freigegebenes Holding-Register skalieren, auf Minimal- und
  Maximalwert prüfen und schreiben.
- **Gerätespezifisch arbeiten:** Die Register werden als JSON konfiguriert und können damit an Modell,
  Firmware und Anlagenkonfiguration angepasst werden.
- **Mehrere MCP-Oberflächen bedienen:** Funktionen werden sowohl als MCP-Tools als auch als
  MCP-Resources angeboten.
- **Lokal bleiben:** Die Verbindung zur Wärmepumpe erfolgt aus dem eigenen Netzwerk; der Server
  benötigt keinen Cloud-Zugang.

### Verfügbare MCP-Tools

| Tool | Zweck | Beispiel |
|---|---|---|
| `list_entities` | Alle konfigurierten Entities und Metadaten anzeigen | „Welche Wärmepumpenwerte kannst du lesen?“ |
| `read_entity` | Aktuellen Wert eines Entity lesen | „Lies `heating.outside_temperature` aus.“ |
| `write_entity` | Einen ausdrücklich erlaubten Wert setzen | „Setze den freigegebenen Sollwert auf 21 °C.“ |

### Verfügbare MCP-Resources

| Resource | Inhalt |
|---|---|
| `idm://entities` | Liste aller konfigurierten Entities |
| `idm://entities/{name}` | Aktueller Wert eines bestimmten Entity |

Welche konkreten Temperaturen, Betriebszustände oder Sollwerte verfügbar sind, entscheidet allein
die lokale `registers.json`. Ohne konfigurierte Entities liefert `list_entities` eine leere Liste.

## Sicherheitskonzept

Der Server startet grundsätzlich **read-only**. Ein Schreibzugriff wird nur ausgeführt, wenn alle
drei Bedingungen gleichzeitig erfüllt sind:

1. `IDM_ALLOW_WRITES=true` aktiviert Schreiben global,
2. das betreffende Entity besitzt `"writable": true`, und
3. seine Adresse steht zusätzlich in `IDM_WRITABLE_ADDRESSES`.

Optionale `minimum`- und `maximum`-Werte begrenzen den erlaubten Sollwert zusätzlich. So führt weder
eine ungenaue Formulierung noch ein einzelner fehlerhafter Konfigurationseintrag automatisch zu
einem Schreibzugriff. Trotzdem müssen alle Adressen und Grenzen fachlich geprüft werden. Weitere
Hinweise stehen unter [Sicherer Betrieb](docs/safety.md).

## Voraussetzungen

- IDM-Wärmepumpe mit aktiviertem und im LAN erreichbarem Modbus TCP
- für das konkrete Gerät und die Firmware verifizierte Registeradressen
- Python 3.11 oder neuer oder alternativ Docker
- ein lokaler MCP-Client mit `stdio`-Unterstützung

## Schnellstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
cp .env.example .env
cp config/registers.example.json config/registers.json
# .env und registers.json an das eigene Gerät anpassen
idm-mcp
```

Die Beispieladressen sind **keine echten bzw. universellen IDM-Adressen**. Register können je nach
Modell, Firmware und Anlagenkonfiguration abweichen. Nur verifizierte Adressen verwenden.

Danach wird die gewünschte KI-Anwendung gemäß der
[clientbezogenen Anleitung](docs/clients.md) eingerichtet. Ein sinnvoller erster Test im Client ist:

> Liste alle konfigurierten IDM-Entities auf. Schreibe keine Werte.

Anschließend kann ein tatsächlich konfiguriertes Entity gelesen werden:

> Lies `heating.outside_temperature` und erkläre Wert und Einheit. Verändere nichts.

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

- nur einzelne 16-Bit-Register (`uint16` und `int16`), noch keine 32-Bit-, Float-, String- oder
  Bitfeld-Entities,
- keine automatische Erkennung von Modell, Firmware oder Registertabelle,
- keine mitgelieferte universelle IDM-Registerliste,
- keine Zeitreihen, Statistiken, Diagramme oder lokale Datenbank,
- aktuell nur lokaler MCP-Transport über `stdio`, kein öffentlicher HTTPS-Endpunkt,
- keine Authentifizierung innerhalb von Modbus TCP.

Diese Einschränkungen sind bewusst sichtbar dokumentiert, damit der Server nicht mit Fähigkeiten
eingesetzt wird, die er derzeit nicht besitzt.

## Lizenz

Der Quellcode steht unter der [MIT-Lizenz](LICENSE). Sie erlaubt Nutzung, Änderung und Weitergabe
unter Beibehaltung des Lizenz- und Copyright-Hinweises und enthält einen Gewährleistungs- und
Haftungsausschluss. Der ergänzende [Disclaimer](DISCLAIMER.md) erklärt Projektstatus und Betriebsrisiken
in verständlicher Form; er ersetzt keine Rechtsberatung.
