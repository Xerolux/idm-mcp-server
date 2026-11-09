# Installation

## Voraussetzungen

- Python 3.12 oder neuer
- Netzwerkzugriff und aktiviertes Modbus TCP an der Wärmepumpe
- ein MCP-Client mit Unterstützung für lokale `stdio`-Server

Die Registerkarte und Modell-Erkennung bringt [idm-heatpump-api](https://github.com/Xerolux/idm-heatpump-api)
mit; eigene Registeradressen müssen nicht mehr gepflegt werden.

## Python

```bash
git clone <REPOSITORY-URL>
cd idm-mcp-server
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install .
cp .env.example .env
```

Unter Windows PowerShell lautet die Aktivierung `.venv\Scripts\Activate.ps1`. Danach in `.env`
mindestens `IDM_HOST` setzen. Modell und Registerkarte werden beim ersten Verbindungsaufbau
automatisch erkannt (`detect_model`).

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
