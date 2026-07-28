# Application Assistant

Der Application Assistant unterstützt die lokale Verwaltung von Profilen,
Stellenanzeigen, Matchings und Bewerbungsständen. Die Kernanwendung läuft
unabhängig von Dify und MinerU: Dify übernimmt ausgewählte LLM-Workflows,
MinerU dient als OCR- und Layout-Fallback für schwierige PDFs.

## Aktueller Funktionsumfang

- kanonische, deutsch/englische Profilverwaltung
- kontrollierter CV-Import mit Konflikt- und Duplikatprüfung
- Import von Stellenanzeigen per URL, PDF oder HTML/SingleFile
- persistente Jobliste mit strukturierten Metadaten und Detailansicht
- evidenzbasiertes Matching gegen ein ausgewähltes Profil
- Bewerbungsstatus, Ereignisverlauf und Dashboard-Kennzahlen
- filterbares Dashboard und zentrale Verwaltungsoberfläche

Die Anwendung ist derzeit für den privaten lokalen Betrieb vorgesehen. Die
Oberflächen besitzen noch keine Anmeldung und dürfen nicht öffentlich
bereitgestellt werden.

## Oberflächen

Nach dem Start sind die wichtigsten Bereiche unter folgenden Adressen
erreichbar:

| Bereich | Adresse |
|---|---|
| Bewerbungsdashboard | `http://localhost:8080/` |
| Zentralverwaltung und Jobimport | `http://localhost:8080/manage` |
| Jobübersicht | `http://localhost:8080/jobs` |
| Profilverwaltung und CV-Import | `http://localhost:8080/profiles/admin` |
| Matching | `http://localhost:8080/matching/admin` |
| API-Dokumentation (Entwicklung) | `http://localhost:8080/docs` |
| Dify | `http://localhost:8088/` |

## Schnellstart mit Docker

Vorausgesetzt werden Docker Desktop sowie bereits laufende Dify-, PostgreSQL-,
Redis- und MinerU-Dienste im gemeinsamen Docker-Netzwerk.

1. Lokale Konfiguration anlegen:

   ```powershell
   Copy-Item .env.example .env
   ```

2. In `.env` mindestens die Datenbankverbindung eintragen. Für den direkten
   CV-Import und das Matching aus der GUI zusätzlich die API-Schlüssel der
   veröffentlichten Dify-Workflows hinterlegen.

3. Backend bauen und starten:

   ```powershell
   docker compose up -d --build
   ```

   Backend restarten:
   ```powershell
   docker compose up -d --force-recreate application-assistant-backend
   ```

   Beim Containerstart werden ausstehende Alembic-Migrationen automatisch
   ausgeführt.

4. Zustand prüfen:

   ```powershell
   docker compose ps
   Invoke-RestMethod http://localhost:8080/health
   ```

5. Optional die vollständige lokale Startbereitschaft von Backend und Dify
   prüfen:

   ```powershell
   .\scripts\check-local-readiness.ps1
   ```

## Bedienungsablauf

1. In der Profilverwaltung ein Zielprofil anlegen oder auswählen.
2. Profildaten manuell pflegen oder eine CV-PDF als prüfbare Vorschläge
   importieren.
3. Vorschläge prüfen und Konflikte beziehungsweise Duplikate bewusst auflösen.
4. In der Zentralverwaltung eine Stellenanzeige per URL importieren.
5. Bei gesperrten oder dynamischen Seiten den Browserabruf versuchen oder die
   Anzeige als PDF beziehungsweise HTML/SingleFile importieren.
6. Den gespeicherten Job öffnen und das Matching für das gewünschte Profil
   starten.
7. Bewerbungsstatus und Kommunikationsereignisse auf der Jobdetailseite
   pflegen.
8. Fortschritt und offene Stellen im Dashboard verfolgen und über die
   Kennzahlen filtern.

Ein Import wird nur gespeichert, wenn ausreichend verwertbarer Inhalt
vorliegt. CV-Importe überschreiben das kanonische Profil niemals automatisch.

## Tests

Die reproduzierbare Testausführung erfolgt über das Test-Image:

```powershell
docker build --target test -t application-assistant-backend:test backend
docker run --rm application-assistant-backend:test
```

## Weiterführende Dokumentation

- [Technischer Projektkontext](project_context.md)
- [Architektur](docs/architecture.md)
- [Backend-API](docs/api.md)
- [Profilverwaltung](docs/profile-management.md)
- [Dify-Anleitung](docs/Dify-Anleitung.md)
- [Dify-Workflow-Übergabe](workflow/dify/README.md)
- [MinerU-Setup](docs/MinerU_Setup.md)
- [Start- und Deployment-Readiness](docs/deployment-readiness.md)
- [Entwicklungsplan](docs/Application_Assistant_Entwicklungsplan_mit_Dity_v3.md)

Bestehende Dify-Sicherungen unter `workflow/backup` werden nicht verändert.
Importierbare, versionierte DSL-Dateien liegen unter `workflow/dify`.
