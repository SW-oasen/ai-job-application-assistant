# Application Assistant

Der Application Assistant ist eine lokal betriebene Webanwendung zur
Verwaltung von Profilen, Stellenanzeigen, Matchings und Bewerbungsverläufen.
Die Kernanwendung läuft unabhängig von Dify und MinerU: Dify übernimmt
ausgewählte LLM-Workflows, MinerU dient als OCR- und Layout-Fallback für
schwierige PDFs.

## Funktionsumfang

- kanonische deutsch- und englischsprachige Profilverwaltung
- kontrollierter CV-Import mit Konflikt- und Duplikatprüfung
- Jobimport per URL, PDF oder HTML/SingleFile
- PDF-Reimport unter Beibehaltung von Job-ID und Bewerbungsdaten
- editierbare Job-Metadaten und persistente Jobliste
- regelbasierte und optional semantische Metadatenextraktion mit Fundstellen
- evidenzbasiertes, profilspezifisches Matching
- Bewerbungsstatus und bearbeitbarer Ereignisverlauf
- Archivierung tatsächlich versendeter Bewerbungs-PDFs
- getrennte Erfassung von Quellportal und Bewerbungsweg
- Dashboard mit Statusfiltern und Stichwortsuche

Portfolio-Projekte, persönliche Karriereziele und ein davon getrennter
Ziel-Fit sind geplante Erweiterungen. Der aktuelle Plan steht in der
[Roadmap](docs/roadmap.md).

## Datenschutz und Netzwerk

Die Anwendung ist für den privaten lokalen Betrieb vorgesehen. Sie besitzt
keine Benutzeranmeldung. `compose.yaml` bindet den Host-Port deshalb
ausschließlich an `127.0.0.1`; die Weboberflächen sind nicht aus dem LAN oder
Internet erreichbar.

Die lokale `.env`, Datenbanken, Bewerbungsunterlagen und Workflow-Sicherungen
werden nicht versioniert. Echte Lebensläufe oder andere personenbezogene
Dokumente gehören nicht in das Repository.

## Oberflächen

| Bereich | Adresse |
|---|---|
| Bewerbungsdashboard | `http://localhost:8080/` |
| Zentralverwaltung und Jobimport | `http://localhost:8080/manage` |
| Jobübersicht | `http://localhost:8080/jobs` |
| Profilverwaltung und CV-Import | `http://localhost:8080/profiles/admin` |
| Matching | `http://localhost:8080/matching/admin` |
| API-Dokumentation in Entwicklung | `http://localhost:8080/docs` |
| Dify | `http://localhost:8088/` |

## Voraussetzungen

- Docker Desktop
- vorhandene Dify-, PostgreSQL-, Redis- und MinerU-Dienste
- gemeinsames Docker-Netzwerk, standardmäßig `docker_default`
- veröffentlichte Dify-Workflows für die gewünschten KI-Funktionen

## Schnellstart

1. Konfiguration anlegen:

   ```powershell
   Copy-Item .env.example .env
   ```

2. In `.env` mindestens `DATABASE_URL` eintragen. Für CV-Import, Matching und
   semantische Job-Metadaten zusätzlich die jeweiligen Dify-API-Schlüssel
   hinterlegen.

3. Backend bauen und starten:

   ```powershell
   docker compose up -d --build
   ```

4. Zustand prüfen:

   ```powershell
   docker compose ps
   Invoke-RestMethod http://localhost:8080/health
   .\scripts\check-local-readiness.ps1
   ```

Beim Containerstart werden ausstehende Alembic-Migrationen automatisch
ausgeführt.

## Bedienungsablauf

1. Profil anlegen oder auswählen.
2. Profildaten manuell pflegen oder eine CV-PDF als prüfbare Vorschläge
   importieren.
3. Vorschläge und mögliche Konflikte bewusst prüfen.
4. Stellenanzeige per URL, PDF oder HTML importieren.
5. Erkannte Metadaten kontrollieren und gegebenenfalls bearbeiten.
6. Matching für das gewünschte Profil ausführen.
7. Bewerbungsstatus, Kommunikationsweg und Verlauf pflegen.
8. Tatsächlich versendete Unterlagen am Bewerbungsdatensatz archivieren.
9. Offene Stellen und Bewerbungen im Dashboard filtern oder durchsuchen.

Ein Import wird nur gespeichert, wenn ausreichend verwertbarer Inhalt
vorliegt. CV-Importe überschreiben das kanonische Profil niemals automatisch.

## Tests

Die reproduzierbare Testausführung erfolgt über das Test-Image:

```powershell
docker build --target test -t application-assistant-backend:test backend
docker run --rm application-assistant-backend:test
```

## Dokumentation

| Dokument | Inhalt |
|---|---|
| [Architektur und technischer Kontext](docs/architecture.md) | Systemgrenzen, Konfiguration und Datenhaltung |
| [Backend-API](docs/api.md) | aktuelle Endpunkte und Sicherheitsgrenzen |
| [Profilverwaltung](docs/profile-management.md) | Profilpflege und CV-Vorschläge |
| [Dify-Setup](docs/dify-setup.md) | lokaler Dify-Betrieb |
| [Dify-Workflows](workflow/dify/README.md) | Import und Veröffentlichung der DSLs |
| [MinerU-Setup](docs/mineru-setup.md) | OCR-Dienst lokal betreiben |
| [Betrieb und Readiness](docs/deployment.md) | Startprüfung und Diagnose |
| [Roadmap](docs/roadmap.md) | aktueller Arbeitsplan |
| [Lernprotokoll](docs/learning-journal.md) | knappe Entwicklungsnotizen |
| [Evaluation](docs/evaluation.md) | Referenzstellen und Qualitätsprüfung |
| [Historischer Entwicklungsplan](docs/historical-development-plan.md) | ursprüngliche Planungsgrundlage |

## Lizenz

Veröffentlicht unter der [MIT-Lizenz](LICENSE).
