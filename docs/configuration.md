# Konfiguration

| Variable | Standard | Bedeutung |
|---|---:|---|
| `IDM_HOST` | leer | IP-Adresse/Hostname; erforderlich |
| `IDM_PORT` | `502` | Modbus-TCP-Port |
| `IDM_UNIT_ID` | `1` | Modbus Unit-ID |
| `IDM_TIMEOUT` | `5.0` | Timeout in Sekunden |
| `IDM_REGISTER_MAP` | leer | Pfad zur JSON-Registerdatei |
| `IDM_ALLOW_WRITES` | `false` | Globaler Schreibschalter |
| `IDM_WRITABLE_ADDRESSES` | leer | Kommagetrennte Adress-Allowlist |

Ein Entity definiert `name`, nullbasierte `address`, `register_type` (`holding`/`input`), `data_type`
(`uint16`/`int16`), `scale`, `offset`, `unit` und optional Schreibgrenzen. Die Umrechnung lautet
`value = raw * scale + offset`.

Schreiben funktioniert nur, wenn gleichzeitig `IDM_ALLOW_WRITES=true`, am Entity `writable=true`
und dessen Adresse in `IDM_WRITABLE_ADDRESSES` gesetzt ist. Zusätzlich immer plausible `minimum`-
und `maximum`-Grenzen konfigurieren.
