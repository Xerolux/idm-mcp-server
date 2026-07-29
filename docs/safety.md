# Sicherer Betrieb

1. Zunächst nur lesbare Entities konfigurieren.
2. Automatisch erkanntes Modell, Firmware, Komponenten und Registermetadaten kontrollieren.
3. Das System mehrere Tage ausschließlich lesend beobachten.
4. Vor Änderungen die Ausgangskonfiguration dokumentieren.
5. Nur einzelne, fachlich geprüfte API-Namen über `IDM_WRITABLE_ENTITIES` freigeben.
6. Jede Schreibaktion bestätigen und anschließend an der Anlage kontrollieren.

Port 502 niemals weiterleiten, Zugriffe per Firewall/VLAN beschränken und Fernzugriff nur über ein
abgesichertes VPN erlauben. Sicherheits-, Frostschutz- und Hygieneparameter nicht ohne Fachbetrieb
verändern. Der Server ersetzt weder die interne Regelung noch Sicherheitseinrichtungen.

Siehe auch den [vollständigen Disclaimer](../DISCLAIMER.md).
