# AGENTS.md

Arbeitsrichtlinien für Coding-Agenten in diesem Repository.

## Projekt

`idm-heatpump-mcp` ist ein MCP-Server (stdio & Streamable HTTP) für IDM-Wärmepumpen.
Die gesamte Gerätekommunikation läuft über [`idm-heatpump-api`](https://github.com/Xerolux/idm-heatpump-api)
(Registerkarte, Modellerkennung, Write-Sicherheit, Web-Clients) – **nie** direkt
über pymodbus und **nie** mit eigenen Registeradressen. Registerfragen werden in
der API gelöst, nicht hier.

## Struktur

- `src/idm_mcp/config.py` – pydantic-Settings (`IDM_*`-Env, `.env`)
- `src/idm_mcp/service.py` – Modbus-Logik, Write-Gates, Poller, Cyclic-Pflege
- `src/idm_mcp/web.py` – Web-Supplement (Nav10-WS/Nav20-HTTP), Gates je Aktion
- `src/idm_mcp/server.py` – FastMCP-Tools/Resources, Lifespan-Poller, Transporte
- `tests/` – pytest mit `FakeTransport` + `FakeWebClient` (keine echte Anlage nötig)

## Befehle

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
pytest tests/ -v          # Tests
ruff check src tests      # Lint
ruff format --check src tests
idm-mcp                   # Server starten (stdio)
```

## Regeln

1. **Sicherheit zuerst:** Schreibvorgänge bleiben standardmäßig deaktiviert.
   Neue Schreibpfade MÜSSEN durch `IdmService._gate_write` bzw.
   `_gate_web_write` (Write-Klasse + Allowlist) laufen. `validate_write`/
   Dry-Run darf niemals Geräte-I/O auslösen.
2. **API-Änderungen:** Kompatibilität nur gegen die öffentliche API von
   `idm_heatpump` (snapshot-getestet in der API); keine privaten Attribute.
   Beim Versionstan der API beachten: Pin in `pyproject.toml` anheben und
   `CHANGELOG.md` ergänzen.
3. **Tests:** Jedes neue Feature bekommt Tests gegen die Fakes; Live-Tests
   gegen echte Anlagen nur lesend (`IDM_ALLOW_WRITES` ungesetzt) und nie in CI.
4. **Doku:** README-Tooltabellen, `docs/configuration.md` (Variablen) und
   `docs/safety.md` bei Verhaltensänderungen mitpflegen. Neue Versionen
   erhalten einen `CHANGELOG.md`-Eintrag.
5. **Style:** Ruff (line-length 100, py312), `ruff format` vor dem Commit.
