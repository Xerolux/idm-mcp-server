# Sicherer Betrieb

1. Zunächst ausschließlich lesend betreiben: `IDM_ALLOW_WRITES` bleibt `false`.
2. Mit `detect_model` die erkannte Anlage prüfen (Modell, Heizkreise, Zonenmodule).
3. Das System mehrere Tage ausschließlich lesend beobachten (`read_all_datapoints`).
4. Vor Änderungen die Ausgangskonfiguration dokumentieren.
5. Nur einzelne, fachlich geprüfte Register freigeben: `IDM_WRITE_CLASSES` klein halten
   (z. B. nur `volatile`) und `IDM_WRITABLE_KEYS` auf konkrete Registernamen einschränken.
6. Jeden Schreibplan zuerst mit `validate_write` bzw. `dry_run=true` prüfen.
7. Jede Schreibaktion bestätigen und anschließend an der Anlage kontrollieren.

Die Write-Klassen helfen bei der Einschätzung: `eeprom`-Register sind dauerhaft
und verschleißbehaftet (die API erlaubt max. einen Schreibzugriff pro Register
und 60 s), `cyclic`-Register erwarten ein zyklisches Erneuern (sonst verwirft
der Controller den Wert), `write_only` sind reine Trigger wie
`error_acknowledge`. Sicherheits-, Frostschutz- und Hygieneparameter nicht ohne
Fachbetrieb verändern.

Web-Schreibaktionen (Betriebsmodus, Warmwasser-Sollwert, Quittierung, Uhrzeit)
folgen derselben Freigabelogik über die Write-Klasse ihrer Modbus-Äquivalente –
sie sind nicht „leichter“ zu erreichen, nur weil sie über das Web-Interface
laufen. Das Web-Supplement benötigt die im Controller gesetzte Web-PIN; sie
gehört nicht in Logs oder Screenshots.

Betrieb mit `IDM_TRANSPORT=http`: nur an `127.0.0.1` binden (Standard) oder
einen Reverse-Proxy mit TLS und Zugangsbeschränkung vorschalten. Der
HTTP-Endpunkt selbst hat keine Authentifizierung – ein statischer
Bearer-Token (`IDM_HTTP_TOKEN`) ist eine Mindestabsicherung, ersetzt aber
keine TLS-Terminierung.

Port 502 niemals weiterleiten, Zugriffe per Firewall/VLAN beschränken und Fernzugriff nur über ein
abgesichertes VPN erlauben. Der Server ersetzt weder die interne Regelung noch Sicherheitseinrichtungen.

Siehe auch den [vollständigen Disclaimer](../DISCLAIMER.md).
