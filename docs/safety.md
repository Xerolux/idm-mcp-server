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

Port 502 niemals weiterleiten, Zugriffe per Firewall/VLAN beschränken und Fernzugriff nur über ein
abgesichertes VPN erlauben. Der Server ersetzt weder die interne Regelung noch Sicherheitseinrichtungen.

Siehe auch den [vollständigen Disclaimer](../DISCLAIMER.md).
