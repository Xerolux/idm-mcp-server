# Installation

## Voraussetzungen

- Python 3.11 oder neuer
- Netzwerkzugriff und aktiviertes Modbus TCP an der Wärmepumpe
- für das konkrete Modell verifizierte Registeradressen
- ein MCP-Client mit Unterstützung für lokale `stdio`-Server

## Python

```bash
git clone <REPOSITORY-URL>
cd idm-mcp-server
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
cp .env.example .env
cp config/registers.example.json config/registers.json
```

Unter Windows PowerShell lautet die Aktivierung `.venv\Scripts\Activate.ps1`. Danach in `.env`
mindestens `IDM_HOST` und `IDM_REGISTER_MAP` setzen und die Beispielregister ersetzen.

```bash
idm-mcp
```

Der Server wartet über die Standardeingabe auf MCP-Nachrichten. Ein leeres Terminal ist normal.
Schreibzugriffe bei der Inbetriebnahme nicht aktivieren.

## Docker

```bash
cp .env.example .env
docker compose build
docker compose run --rm -i idm-mcp
```

Der MCP-Client muss Ein- und Ausgabe des Containers anbinden. Für Desktop-Clients ist die lokale
Installation meist einfacher.

## Nächster Schritt

Nach der Installation den Server anhand der
[Anleitung für den verwendeten MCP-Client](clients.md) einbinden. Dort sind Beispiele für Claude,
ChatGPT, GitHub Copilot, Codex und Z.ai sowie Hinweise zu deren unterschiedlichen Transporten
aufgeführt.
