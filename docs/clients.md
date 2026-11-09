# MCP-Clients einrichten

Diese Seite beschreibt die Einbindung in verbreitete KI-Clients. Produktoberflächen und Menünamen
können sich mit Updates ändern. Entscheidend ist die Unterscheidung zwischen:

- **lokalem MCP über `stdio`**: Der Client startet `idm-mcp` auf demselben Rechner. Das unterstützt
  dieser Server direkt.
- **entferntem MCP über HTTPS**: Ein Webdienst verbindet sich mit einer öffentlich erreichbaren,
  authentifizierten URL. Das unterstützt dieses Projekt derzeit bewusst **nicht**.

## Vorbereitungen für alle lokalen Clients

Zuerst die [Installation](installation.md) abschließen. Anschließend absolute Pfade ermitteln:

```bash
cd /pfad/zu/idm-mcp-server
pwd
realpath .venv/bin/idm-mcp
```

Unter Windows beispielsweise:

```powershell
(Resolve-Path .venv\Scripts\idm-mcp.exe).Path
```

In den Beispielen müssen diese Platzhalter ersetzt werden:

| Platzhalter | Beispiel |
|---|---|
| `<IDM-MCP>` | `/home/user/idm-mcp-server/.venv/bin/idm-mcp` |
| `<WÄRMEPUMPE>` | `192.168.1.50` |

Der Client muss im selben LAN bzw. VPN wie die Wärmepumpe laufen. Zum Einstieg bleibt
`IDM_ALLOW_WRITES` absichtlich ungesetzt.

## Claude Desktop

Claude Desktop kann einen lokalen MCP-Server über seine Desktop-Konfiguration starten. Die Datei
heißt `claude_desktop_config.json` und liegt üblicherweise hier:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Bestehende `mcpServers`-Einträge nicht überschreiben, sondern den neuen Eintrag ergänzen:

```json
{
  "mcpServers": {
    "idm-heatpump": {
      "command": "<IDM-MCP>",
      "args": [],
      "env": {
        "IDM_HOST": "<WÄRMEPUMPE>",
        "IDM_PORT": "502",
        "IDM_SLAVE_ID": "1",
        "IDM_ALLOW_WRITES": "false"
      }
    }
  }
}
```

Claude Desktop vollständig beenden und neu starten. In den Einstellungen bzw. im Tool-Menü prüfen,
ob `idm-heatpump` und die Tools `detect_model`, `list_datapoints`, `read_datapoint` und
`write_datapoint` erscheinen. Zuerst `detect_model` und danach `read_datapoint` für einen
Messwert (z. B. `outdoor_temp`) testen.

## Claude Code

Für eine projektbezogene Claude-Code-Konfiguration kann im Projekt eine `.mcp.json` mit demselben
Schema angelegt werden:

```json
{
  "mcpServers": {
    "idm-heatpump": {
      "type": "stdio",
      "command": "<IDM-MCP>",
      "args": [],
      "env": {
        "IDM_HOST": "<WÄRMEPUMPE>",
        "IDM_ALLOW_WRITES": "false"
      }
    }
  }
}
```

Die Datei nur committen, wenn sie keine privaten IP-Adressen oder andere lokale Informationen
enthält. Alternativ die benutzerspezifische MCP-Konfiguration bzw. den MCP-Dialog von Claude Code
verwenden. Nach dem Start mit `/mcp` Status und Tools kontrollieren.

## OpenAI Codex CLI bzw. Codex IDE-Erweiterung

Codex liest lokale MCP-Server aus `~/.codex/config.toml`. Folgenden Abschnitt ergänzen:

```toml
[mcp_servers.idm-heatpump]
command = "<IDM-MCP>"
args = []

[mcp_servers.idm-heatpump.env]
IDM_HOST = "<WÄRMEPUMPE>"
IDM_PORT = "502"
IDM_SLAVE_ID = "1"
IDM_ALLOW_WRITES = "false"
```

Danach Codex neu starten und den MCP-Status kontrollieren. Je nach installierter Codex-Version kann
der Server auch per CLI registriert werden; `codex mcp --help` zeigt die für diese Version gültigen
Unterbefehle. Die TOML-Variante ist dokumentierbarer und vermeidet versionsabhängige CLI-Flags.

## ChatGPT im Browser oder als Desktop-App

Die obigen Konfigurationen dürfen **nicht** ungeprüft in ChatGPT kopiert werden. Die ChatGPT-
Weboberfläche ist ein gehosteter Dienst und kann den lokalen Prozess `<IDM-MCP>` oder eine private
LAN-Adresse nicht direkt erreichen. Welche MCP-Optionen die Desktop-App anbietet, kann von Version,
Tarif und Workspace-Richtlinien abhängen. Nur wenn die installierte App ausdrücklich lokale
`stdio`-Server unterstützt, ist eine direkte lokale Einbindung möglich; andernfalls wird ein über
HTTPS erreichbarer MCP-Endpunkt mit angemessener Authentifizierung benötigt.

Dieses Repository stellt derzeit absichtlich nur `stdio` bereit und enthält weder HTTPS-Transport,
Authentifizierung noch Benutzerverwaltung. Damit ist eine direkte ChatGPT-Web-Einbindung **noch
nicht enthalten**. Keinesfalls Port 502 oder die Wärmepumpe selbst veröffentlichen. Eine spätere
Remote-Variante sollte über einen separaten Gateway mit TLS, Anmeldung, Autorisierung, Rate-Limits,
Audit-Log und weiterhin deaktivierten Schreibrechten umgesetzt werden.

Bis dahin kann der Server lokal mit Codex oder einem anderen `stdio`-fähigen MCP-Client verwendet
werden. Ein unsicherer Tunnel ist keine akzeptable Abkürzung.

## GitHub Copilot in Visual Studio Code

Gemeint ist hier **GitHub Copilot in VS Code**, nicht die Website GitHub.com. In einem Workspace kann
eine `.vscode/mcp.json` angelegt werden:

```json
{
  "servers": {
    "idm-heatpump": {
      "type": "stdio",
      "command": "<IDM-MCP>",
      "args": [],
      "env": {
        "IDM_HOST": "<WÄRMEPUMPE>",
        "IDM_ALLOW_WRITES": "false"
      }
    }
  }
}
```

Danach den Server in der MCP-Ansicht von VS Code starten und Copilot in den Agent-Modus wechseln.
Bei verwalteten Firmenkonten können Administratorrichtlinien lokale MCP-Server sperren. Lokale IPs
nicht versehentlich in ein öffentliches Repository committen.

GitHub.com selbst kann keinen Prozess im Heimnetz starten. GitHub Actions eignen sich ebenfalls
nicht für diesen Zweck: Hosted Runner befinden sich nicht im lokalen Wärmepumpennetz und Secrets
bzw. öffentlich geöffnete Modbus-Ports wären ein unnötiges Sicherheitsrisiko.

## Z.ai und GLM-basierte Clients

„Z.ai“ bezeichnet mehrere Web-, API- und Coding-Angebote. Ob lokales MCP unterstützt wird und wie
die Konfiguration heißt, hängt vom konkret verwendeten Client und dessen Version ab:

- Unterstützt der Client lokale `stdio`-Server und ein `mcpServers`-Schema, kann grundsätzlich die
  Konfiguration aus dem Abschnitt **Claude Desktop** übernommen werden.
- Unterstützt er ausschließlich entfernte MCP-URLs oder nur die Z.ai-Weboberfläche, ist dieser
  lokale Server nicht direkt einbindbar.
- Wird GLM über einen Drittclient wie eine IDE-Erweiterung verwendet, wird MCP im Drittclient
  konfiguriert – nicht beim Modellanbieter.

Nicht ungeprüft von einer beliebigen Oberfläche auf MCP-Unterstützung schließen. In der aktuellen
Dokumentation des konkret verwendeten Z.ai-Clients nach `MCP`, `stdio` und `local server` suchen. Bei
einer reinen Weboberfläche gelten dieselben Remote- und Sicherheitshinweise wie für ChatGPT.

## HTTP-Transport statt stdio

Für Container-, Server- oder LAN-Betrieb kann der Server als Streamable-HTTP-Endpunkt laufen
statt als lokaler `stdio`-Prozess:

```bash
IDM_TRANSPORT=http IDM_HTTP_PORT=8308 idm-mcp
# Endpunkt: http://127.0.0.1:8308/mcp
```

Schnelltest:

```bash
curl -s http://127.0.0.1:8308/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
```

Der Standard bindet bewusst an `127.0.0.1`. Clients, die Remote-MCP-URLs unterstützen
(Claude Desktop mit Connectors, ChatGPT Desktop u. a.), brauchen eine über HTTPS erreichbare,
authentifizierte URL: den Server dazu hinter einen Reverse-Proxy mit TLS und
Zugangsbeschränkung setzen und per `IDM_HTTP_HOST` nur auf die Proxy-Gegenstelle binden.
Der Endpunkt selbst hat keine eigene Authentifizierung – niemals direkt ins LAN oder Internet
exponieren, und den Modbus-Port der Wärmepumpe schon gar nicht.

## Funktion prüfen

Nach der Einrichtung in jedem Client in dieser Reihenfolge testen:

1. Ist der Serverstatus verbunden bzw. grün?
2. Liefert `detect_model` die erwartete Anlage (Modell, Heizkreise)?
3. Liefert `read_datapoint` für **einen Messwert** (z. B. `outdoor_temp`) einen plausiblen Wert?
4. Bleibt ein Schreibversuch mit `writes are disabled` gesperrt?

Wenn der Server nicht startet, zunächst `<IDM-MCP>` im Terminal ausführen. Bei `IDM_HOST is not
configured` fehlt die Umgebungsvariable; bei Verbindungsfehlern Netzwerk, Port, Slave-ID und die
Modbus-Freigabe der Wärmepumpe kontrollieren.
