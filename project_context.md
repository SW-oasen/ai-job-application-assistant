# Technischer Projektkontext

Dieses Dokument enthält die technische Konfiguration und den Betriebsrahmen
des Application Assistant. Nutzerorientierte Start- und Bedienungshinweise
stehen in der [README](README.md).

## Systemgrenzen

Der Application Assistant ist die stabile Kernanwendung. Dify, MinerU,
PostgreSQL und Redis sind externe Dienste und bleiben getrennt aktualisierbar.

```text
Browser
  |
  v
Application Assistant (FastAPI, Port 8080)
  |-- PostgreSQL: kanonische Daten und Ergebnisse
  |-- Redis: konfigurierter Infrastrukturanschluss
  |-- Dify API: CV-Extraktion, semantische Job-Metadaten und Matching
  `-- MinerU: OCR-/Layout-Fallback für PDF-Importe
```

Das Backend importiert keinen Quellcode aus den Dify-, MinerU- oder
Portfolio-Projekten. Verbindungen erfolgen über HTTP, Datenbanktreiber und
konfigurierbare Dienstnamen.

## Repository-Struktur

| Pfad | Zweck |
|---|---|
| `backend/app` | FastAPI-Anwendung, Geschäftslogik und statische Oberflächen |
| `backend/alembic` | versionierte Datenbankmigrationen |
| `backend/tests` | API- und Unit-Tests |
| `docs` | fachliche und technische Detaildokumentation |
| `workflow/dify` | importierbare, versionierte Dify-DSLs |
| `workflow/backup` | unveränderte Sicherungen früherer Workflows |
| `scripts` | lokale Betriebs- und Readiness-Hilfen |
| `compose.yaml` | Compose-Service der Kernanwendung |
| `.env.example` | Vorlage der lokalen Konfiguration ohne Geheimnisse |

## Laufzeit und Container

- Python: 3.11 oder neuer
- Backend: FastAPI/Uvicorn
- Persistenz: PostgreSQL über SQLAlchemy und Psycopg
- Migrationen: Alembic
- Browser-Fallback: Playwright/Chromium
- Standard-Port auf dem Host: `8080`
- Dify-Weboberfläche im lokalen Setup: `8088`
- gemeinsames externes Docker-Netzwerk: `docker_default`

`compose.yaml` startet ausschließlich
`application-assistant-backend`. Der Container führt vor Uvicorn automatisch
`alembic upgrade head` aus und besitzt einen Healthcheck auf `/health`.

## Konfiguration

Die lokale `.env` wird aus `.env.example` erzeugt und ist durch `.gitignore`
vom Repository ausgeschlossen:

```powershell
Copy-Item .env.example .env
```

Echte Passwörter und API-Schlüssel dürfen weder in Git noch in Workflow-DSLs
oder Browser-Code gespeichert werden.

### Anwendung

| Variable | Standard | Bedeutung |
|---|---|---|
| `APP_ENV` | `development` | Umgebung; in `production` sind Swagger und ReDoc deaktiviert |
| `APP_HOST` | `0.0.0.0` | Bind-Adresse im Container |
| `APP_PORT` | `8080` | veröffentlichter Backend-Port |
| `APP_LOG_LEVEL` | `INFO` | Log-Level |

### Dify

| Variable | Standard | Bedeutung |
|---|---|---|
| `DIFY_BASE_URL` | `http://api:5001` | interne Dify-API-Adresse |
| `DIFY_CV_WORKFLOW_API_KEY` | leer | API-Schlüssel des veröffentlichten CV-PDF-Workflows |
| `DIFY_CV_WORKFLOW_TIMEOUT_SECONDS` | `300` | maximale Laufzeit des CV-Workflows |
| `DIFY_MATCHING_WORKFLOW_API_KEY` | leer | API-Schlüssel des veröffentlichten Matching-v3-Workflows |
| `DIFY_MATCHING_WORKFLOW_TIMEOUT_SECONDS` | `300` | maximale Laufzeit des Matching-Workflows |
| `DIFY_METADATA_WORKFLOW_API_KEY` | leer | API-Schlüssel des semantischen Job-Metadaten-Fallbacks |
| `DIFY_METADATA_WORKFLOW_TIMEOUT_SECONDS` | `120` | maximale Laufzeit des Metadaten-Workflows |
| `SEMANTIC_METADATA_MAX_CHARACTERS` | `15000` | maximal vollständig übergebener Anzeigentext |

Die Schlüssel stammen aus der API-Zugangsseite der jeweiligen veröffentlichten
Dify-App. Der direkte Aufruf aus dem Backend benötigt keine Konfiguration als
„Workflow as Tool“.

### MinerU

| Variable | Standard | Bedeutung |
|---|---|---|
| `MINERU_BASE_URL` | `http://mineru-api:8000` | interne MinerU-Adresse |
| `MINERU_TIMEOUT_SECONDS` | `300` | maximale OCR-Laufzeit |
| `MINERU_BACKEND` | `pipeline` | MinerU-Verarbeitungsbackend |

MinerU wird nur für PDFs verwendet, deren native Textextraktion die
Qualitätsprüfung nicht besteht. Dazu zählen auch auffällig viele
Unicode-Ersatzzeichen. HTML/SingleFile wird lokal verarbeitet.

### Datenhaltung

| Variable | Beispiel | Bedeutung |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://USER:PASSWORD@db_postgres:5432/application_assistant` | eigene Datenbank der Kernanwendung |
| `REDIS_URL` | `redis://redis:6379/0` | Redis-Verbindung |
| `APPLICATION_DOCUMENTS_PATH` | `/app/data/application-documents` | zentraler Ablageort archivierter Bewerbungs-PDFs im Container |
| `APPLICATION_DOCUMENT_MAX_BYTES` | `20000000` | maximale Größe einer Bewerbungs-PDF |

Die Anwendung verwendet die separate Datenbank `application_assistant` auf der
vorhandenen PostgreSQL-Instanz. Dify-Datenbanken und Dify-Tabellen werden nicht
verändert. Die Datenbank muss einmalig vorhanden sein, bevor der Backend-
Container seine Migrationen ausführen kann.

Manueller Migrationslauf:

```powershell
docker compose run --rm application-assistant-backend alembic upgrade head
```

SQL-Zugriff erfolgt beispielsweise über `psql` im vorhandenen
PostgreSQL-Container:

```powershell
docker exec -it docker-db_postgres-1 `
  psql -U postgres -d application_assistant
```

Zugangsdaten werden ausschließlich der lokalen `.env` beziehungsweise der
PostgreSQL-Konfiguration entnommen und hier nicht dokumentiert.

Archivierte Lebensläufe, Anschreiben und Anlagen liegen als Dateien im
benannten Docker-Volume `application-documents`. PostgreSQL speichert nur
Dateimetadaten, Prüfsumme und Zuordnung zur Bewerbung. Das Volume bleibt bei
einem normalen Container-Neubau erhalten.

### Importgrenzen

| Variable | Standard | Bedeutung |
|---|---:|---|
| `URL_IMPORT_TIMEOUT_SECONDS` | `30` | Timeout eines HTTP-Imports |
| `URL_IMPORT_MAX_BYTES` | `10000000` | maximales URL-Dokument |
| `URL_IMPORT_MIN_TEXT_LENGTH` | `500` | Mindestlänge für ausreichenden Inhalt |
| `URL_IMPORT_MAX_REDIRECTS` | `5` | maximale Redirect-Anzahl |
| `URL_IMPORT_USER_AGENT` | `ApplicationAssistant/0.1 (+local)` | HTTP User-Agent |
| `PLAYWRIGHT_ENABLED` | `true` | Browser-Fallback aktivieren |
| `PLAYWRIGHT_TIMEOUT_SECONDS` | `45` | Browser-Timeout |
| `PDF_IMPORT_MAX_BYTES` | `20000000` | maximale PDF-Größe |
| `PDF_IMPORT_MIN_TEXT_LENGTH` | `500` | Mindestlänge nativer PDF-Texte |
| `HTML_IMPORT_MAX_BYTES` | `30000000` | maximale HTML-/SingleFile-Größe |

### Docker-Netzwerk

| Variable | Standard | Bedeutung |
|---|---|---|
| `DOCKER_NETWORK_NAME` | `docker_default` | vorhandenes externes Netzwerk von Dify und MinerU |

Interne Standardadressen:

| Dienst | Adresse |
|---|---|
| Application Assistant | `http://application-assistant-backend:8080` |
| Dify API | `http://api:5001` |
| MinerU | `http://mineru-api:8000` |
| PostgreSQL | `db_postgres:5432` |
| Redis | `redis:6379` |

Container-IP-Adressen sind absichtlich nicht fest hinterlegt.

## Dify-SSRF-Freigabe

Dify-HTTP-Nodes erreichen das interne Backend über den SSRF-Proxy. In der
lokalen Dify-Konfiguration wird ausschließlich der benötigte DNS-Name
freigegeben:

```env
SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=application-assistant-backend
```

Anschließend genügt es, den Dify-Proxy neu zu erstellen:

```powershell
cd D:\Projects\AI\Dify\dify-main\docker
docker compose up -d --force-recreate ssrf_proxy
```

Die Freigabe darf nicht pauschal auf private Netzbereiche erweitert werden.

## Dify-Workflows

Aktuell relevant sind:

| DSL | Zweck |
|---|---|
| `workflow/dify/01-import-job-url-v3.yml` | Stellen-URL über das Backend importieren und strukturieren |
| `workflow/dify/00-import_cv_pdf.yml` | CV-PDF extrahieren und Vorschläge beim ausgewählten Profil anlegen |
| `workflow/dify/03-job-metadata-fallback-v1.yml` | fehlende oder unplausible Job-Metadaten mit Fundstellen ergänzen |
| `workflow/dify/02-matching-v3.yml` | Jobtext strukturieren und evidenzbasiertes Matching ausführen |

Workflows werden manuell in Dify importiert, getestet und veröffentlicht.
Eine neue DSL überschreibt keine bestehende Dify-App automatisch. Details zu
Eingaben, Ausgaben und Veröffentlichung stehen in
[workflow/dify/README.md](workflow/dify/README.md).

Die frühere Dokumenterzeugung und der Adapter
`02b-store-cv-profile-proposals` gehören nicht zum aktuellen MVP und bleiben
nur als Sicherung unter `workflow/backup`.

## Daten- und Verarbeitungsregeln

- Ungültige oder qualitativ unzureichende Jobimporte erzeugen keinen Job.
- Identischer Jobinhalt wird per SHA-256 erkannt und nicht doppelt angelegt.
- Ein expliziter PDF-Reimport aktualisiert den vorhandenen Job bei gleicher
  Prüfsumme und behält Job-ID, Bewerbung und archivierte Unterlagen.
- Beim Reimport werden veraltete Anforderungen und Matches entfernt.
- Native PDF-Extraktion fällt bei beschädigten Glyphen oder unzureichender
  Textqualität auf MinerU zurück.
- Ein gemeinsamer Regelparser verarbeitet PDF-, MinerU-, HTML- und URL-Texte.
- Quellportal und Bewerbungsweg sind getrennte Daten. Das Quellportal kann aus
  Dateiname oder URL abgeleitet und als Parserhinweis verwendet werden.
- Der semantische Metadaten-Fallback läuft nur bei fehlenden Pflichtfeldern
  oder unplausiblen Werten. Automatische Übernahme erfordert mindestens `0,85`
  Konfidenz und eine im Ausgangstext überprüfbare Fundstelle.
- Der semantische Fallback darf bestehende sichere Regelwerte nicht
  überschreiben und darf Benefits nicht als Arbeitsmodell interpretieren.
- CV-Importe erzeugen ausschließlich prüfbare Vorschläge.
- Duplikate und Konflikte erfordern eine bewusste Entscheidung.
- Angepasste CV-Profiltexte gelten nicht als kanonische Profildaten.
- Matching verwendet Skills, Berufserfahrung, Ausbildung und Zertifikate.
- Nationalität sowie daraus belegbare Arbeits- und Aufenthaltsberechtigung
  werden als Matching-Evidenz berücksichtigt.
- Referenzen und Kontaktdaten werden nicht als Matching-Evidenz an Dify
  übergeben.
- Änderungen an Profilentitäten erzeugen Revisionssnapshots.
- Portfolio-Daten dürfen künftig ausschließlich lesend angebunden werden.

## Job-Metadatenpipeline

```text
URL / PDF / HTML
  |
  +-- native Extraktion
  |     `-- PDF bei Qualitätsmangel -> MinerU
  |
  +-- gemeinsamer Regelparser
  |     `-- Titel, Firma, Ort, Arbeitsmodell, Beschäftigungsart,
  |         Befristung und Quellportal
  |
  +-- Plausibilitäts- und Vollständigkeitsprüfung
  |     `-- bei Bedarf semantischer Dify-Fallback
  |
  `-- validierte Persistenz mit Warnungen und Fundstellen
```

Der Regelparser bleibt die deterministische Primärstufe und wird anhand realer
Portalvarianten durch Regressionstests erweitert. Der semantische Fallback
erhält den vollständigen Text bis 15.000 Zeichen sowie Dateiname, URL,
Quellportal und bisherige Regelergebnisse. Fehlende optionale Angaben werden
nicht erfunden.

Strukturierte Job-Metadaten bleiben in der Jobdetailansicht manuell editierbar.
Dazu gehören Titel, Firma, Ort, Arbeitsmodell, Beschäftigungsart, Befristung,
Sprache, Veröffentlichungsdatum, Bewerbungsfrist und Quellportal.

## Bewerbungsverlauf

Eine Bewerbung ist einem Job und einem Profil zugeordnet. Statuswechsel und
Kommunikation werden als getrennte Ereignisse geführt. Bei
`channel=job_portal` kann `portal_name` den tatsächlichen Kanal, beispielsweise
LinkedIn oder Indeed, näher beschreiben. Dieser Wert ist unabhängig vom
Quellportal der Stellenanzeige.

## Importsicherheit

Der URL-Import akzeptiert nur öffentliche HTTP(S)-Ziele. Lokale, private und
reservierte Adressen sowie eingebettete Zugangsdaten werden blockiert.
Redirects und Browser-Subrequests werden erneut geprüft. Für gesperrte
Jobportale stehen PDF und lokal verarbeitetes HTML/SingleFile als kontrollierte
Fallbacks bereit.

Die Weboberflächen besitzen derzeit keine Authentifizierung. Der Dienst ist
deshalb nur lokal beziehungsweise in einem vertrauenswürdigen privaten Netz zu
betreiben.

## Entwicklung und Tests

Vollständige Tests im Docker-Test-Image:

```powershell
docker build --target test -t application-assistant-backend:test backend
docker run --rm application-assistant-backend:test
```

Lokale Python-Entwicklung:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

Die `.env` liegt im Workspace-Stamm. Für lokale Tests ohne erreichbare
Persistenz können einzelne API-Funktionen eingeschränkt sein; der reguläre
Betrieb verwendet PostgreSQL.

## Betrieb und Diagnose

```powershell
docker compose up -d --build
docker compose ps
docker compose logs application-assistant-backend
Invoke-RestMethod http://localhost:8080/health
.\scripts\check-local-readiness.ps1
```

Eine HTTP-200-Antwort der Dify-Webseite allein beweist nicht, dass alle
Dify-Komponenten bereits bereit sind. Das Readiness-Skript prüft deshalb auch
den plausiblen Inhalt der Anmeldeseite. Die vollständige Checkliste steht in
[docs/deployment-readiness.md](docs/deployment-readiness.md).

## Technische Detaildokumente

- [Architektur](docs/architecture.md)
- [API](docs/api.md)
- [Profilverwaltung](docs/profile-management.md)
- [Dify-Anleitung](docs/Dify-Anleitung.md)
- [MinerU-Setup](docs/MinerU_Setup.md)
- [Deployment-Readiness](docs/deployment-readiness.md)
- [Entwicklungsplan](docs/Application_Assistant_Entwicklungsplan_mit_Dity_v3.md)
