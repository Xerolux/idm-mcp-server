# Konfiguration

| Variable | Standard | Bedeutung |
|---|---:|---|
| `IDM_HOST` | leer | IP-Adresse/Hostname; erforderlich |
| `IDM_PORT` | `502` | Modbus-TCP-Port |
| `IDM_UNIT_ID` | `1` | Modbus Unit-ID |
| `IDM_TIMEOUT` | `5.0` | Timeout in Sekunden |
| `IDM_AUTO_DETECT` | `true` | Modell und installierte Komponenten automatisch erkennen |
| `IDM_ALLOW_WRITES` | `false` | Globaler Schreibschalter |
| `IDM_WRITABLE_ENTITIES` | leer | Kommagetrennte Allowlist kanonischer API-Namen |
| `MCP_TRANSPORT` | `stdio` | `stdio` oder `http` |
| `MCP_HOST` | `127.0.0.1` | HTTP-Bind-Adresse |
| `MCP_PORT` | `8100` | HTTP-Port |
| `MCP_PATH` | `/mcp` | HTTP-Endpunkt |

Entities und Metadaten stammen aus `idm-heatpump-api`. Der MCP-Server erkennt die Anlage und baut
daraus automatisch die passende Registerkarte. Namen können mit `list_entities` ermittelt werden.

Schreiben funktioniert nur, wenn gleichzeitig `IDM_ALLOW_WRITES=true`, das API-Register als
schreibbar definiert und dessen Name in `IDM_WRITABLE_ENTITIES` gesetzt ist. Jeder Aufruf ist ohne
`dry_run=false` nur eine Simulation; Wertebereiche und Schreibklasse prüft zusätzlich die API.

## HTTP-Transport im lokalen Netz

```bash
idm-mcp --transport http --host 127.0.0.1 --port 8100 --path /mcp
```

Zum Zugriff von einem anderen Rechner kann bewusst eine LAN-Adresse gebunden werden. Ohne
vorgeschaltete Authentifizierung, TLS und Firewall darf der HTTP-Endpunkt weder an `0.0.0.0` in
einem ungeschützten Netz noch öffentlich im Internet betrieben werden. Der Modbus-Port 502 wird
niemals veröffentlicht.
