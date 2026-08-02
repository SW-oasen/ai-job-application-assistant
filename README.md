# Application Assistant

Der Application Assistant ist eine lokal betriebene Webanwendung zur
Verwaltung von Profilen, Stellenanzeigen, Matchings und Bewerbungsverläufen.
Die Kernanwendung läuft unabhängig von Dify und MinerU: Dify übernimmt
ausgewählte LLM-Workflows, MinerU dient als OCR- und Layout-Fallback für
schwierige PDFs.

## Warum dieses Projekt entstanden ist

Ich habe diese Anwendung entwickelt, weil ich mich selbst auf zahlreiche Stellen bewerbe. Sie wird täglich im realen Bewerbungsprozess eingesetzt und kontinuierlich anhand praktischer Erfahrungen erweitert. Neue Funktionen entstehen aus konkreten Anforderungen während der Nutzung – beispielsweise die Browser-Bridge für den direkten Import von Stellenanzeigen oder die Verwaltung des Bewerbungsverlaufs inklusive Archivierung der tatsächlich versendeten Unterlagen.

## Funktionsumfang

- kanonische deutsch- und englischsprachige Profilverwaltung
- strukturiertes berufliches Zielprofil mit davon getrenntem Ziel-Fit
- Portfolio-Projekte als eigene, prüfbare Evidenzquelle inklusive Import aus
  `projects.js`
- kontrollierter CV-Import mit Konflikt- und Duplikatprüfung
- Jobimport per URL, PDF oder HTML/SingleFile
- Ein-Klick-Jobimport über ein Browser-Lesezeichen für komplexe Jobportale wie Indeed
- PDF-Reimport unter Beibehaltung von Job-ID und Bewerbungsdaten
- editierbare Job-Metadaten, persistente Jobliste und Jobarchivierung
- Änderungsverlauf einer Stellenanzeige über mehrere Importe hinweg
- regelbasierte und optional semantische Metadatenextraktion mit Fundstellen
- evidenzbasiertes, profilspezifisches Matching inklusive Senioritätsabgleich
- Bewerbungsstatus und bearbeitbarer Ereignisverlauf
- Archivierung tatsächlich versendeter Bewerbungs-PDFs
- getrennte Erfassung von Quellportal und Bewerbungsweg
- Dashboard mit Statusfiltern und Stichwortsuche (nun auf der Hauptseite)

Der aktuelle Arbeitsplan steht in der [Roadmap](docs/roadmap.md).

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
| Jobs und Bewerbungen (Hauptseite) | `http://localhost:8080/` |
| Zentralverwaltung und Jobimport | `http://localhost:8080/manage` |
| Jobdetails, Matching und Bewerbung | `http://localhost:8080/jobs/{job_id}` |
| Browser-Bridge für Ein-Klick-Jobimport | `http://localhost:8080/browser-import` |
| Profilverwaltung und CV-Import | `http://localhost:8080/profiles/admin` |
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

## Review-Integration (Dify)

Optional kann die Anwendung sogenannte Review-Workflows an Dify auslagern
(z. B. Prüfung von extrahierten Job-Metadaten oder Matching-Qualitätschecks).
Die Review-Workflows sind optional und brechen Importe oder Matchingläufe
nicht ab; fehlerhafte oder fehlgeschlagene Reviews werden in der Review-
Historie protokolliert.

- Konfiguration: In der lokalen `.env` kann `REVIEW_WORKFLOWS` als JSON
   hinterlegt werden. Das Mapping verwendet Dify-App-API-Keys (als Literale
   `app-...`) als Schlüssel; die Workflows werden serverseitig per App-Key
   aufgerufen.
- Beispiel (vereinfachte Form):

   ```text
   REVIEW_WORKFLOWS='{"app-abc123": {"enabled": true, "api_key": "app-abc123"}}'
   ```

- Hinweis: `workflow_id` wird nicht mehr in der Payload erwartet; stattdessen
   wird der App-API-Key verwendet. Die Dify-Workflows erwarten das Feld
   `attempt` als String (nicht als Zahl).
- Nach dem Import/Aktualisierung der Workflows ist die Migration für die
   Review-Historie notwendig (enthält u. a. `review_runs` und `review_issues`).
   Beispiel:

   ```powershell
   docker compose exec application-assistant-backend alembic upgrade head
   ```

Weitere technische Details befinden sich in den Dokumenten unter `docs/`.

## Bedienungsablauf

1. Profil über den Tab `Profil` in der Profilverwaltung anlegen oder
   auswählen.
2. Profildaten manuell pflegen oder eine CV-PDF als prüfbare Vorschläge
   importieren.
3. Vorschläge und mögliche Konflikte bewusst prüfen.
4. Stellenanzeige per URL, PDF oder HTML importieren.
5. Alternativ das Browser-Lesezeichen wie unter `Verwaltung > Stellen importieren > Browser-Import einrichten` erstellen und
   eine geöffnete Stellenanzeige mit einem Klick an die lokale Anwendung senden.
   Auch komplexe Seiten wie Indeed werden dabei automatisch in strukturierte
   Jobdaten umgewandelt.
6. Erkannte Metadaten kontrollieren und gegebenenfalls bearbeiten.
7. Matching für das gewünschte Profil ausführen.
8. Bewerbungsstatus, Kommunikationsweg und Verlauf pflegen.
9. Tatsächlich versendete Unterlagen am Bewerbungsdatensatz archivieren.
10. Offene Stellen und Bewerbungen auf der Hauptseite filtern oder durchsuchen.

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
