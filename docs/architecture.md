# Architektur und technischer Kontext

Dieses Dokument beschreibt Systemgrenzen, Laufzeit, Datenhaltung und zentrale
Verarbeitungsregeln. Einstieg und Bedienung stehen in der
[README](../README.md).

## Systemgrenzen

Der Application Assistant ist die Kernanwendung. Dify, MinerU, PostgreSQL und
Redis sind getrennte Dienste und werden ausschließlich über konfigurierbare
Schnittstellen angesprochen.

```text
Browser
  |
  v
Application Assistant (FastAPI)
  |-- PostgreSQL: kanonische Daten und Ergebnisse
  |-- Redis: konfigurierter Infrastrukturanschluss
  |-- Dify API: CV-Import, CV-Recommender, Job-Metadaten und Matching
  `-- MinerU: OCR- und Layout-Fallback für PDFs
```

Das Backend importiert keinen Quellcode der externen Dienste und verwendet
keine festen Container-IP-Adressen.

## Repository

| Pfad | Zweck |
|---|---|
| `backend/app` | FastAPI-Anwendung, Geschäftslogik und Weboberflächen |
| `backend/alembic` | Datenbankmigrationen |
| `backend/tests` | API-, Integrations- und Unit-Tests |
| `docs` | technische, fachliche und interne Dokumentation |
| `workflow/dify` | importierbare Dify-Workflow-DSLs |
| `scripts` | lokale Betriebs- und Readiness-Hilfen |
| `compose.yaml` | Containerdefinition der Kernanwendung |
| `.env.example` | Konfigurationsvorlage ohne Geheimnisse |

Lokale Workflow-Sicherungen unter `workflow/backup` sind ignoriert und nicht
Bestandteil des öffentlichen Repositorys.

## Laufzeit und Netzwerk

- Python 3.11 oder neuer
- FastAPI und Uvicorn
- PostgreSQL über SQLAlchemy und Psycopg
- Alembic-Migrationen
- Playwright/Chromium als Browser-Fallback
- Docker-Netzwerk standardmäßig `docker_default`

Interne Standardadressen:

| Dienst | Adresse |
|---|---|
| Application Assistant | `http://application-assistant-backend:8080` |
| Dify API | `http://api:5001` |
| MinerU | `http://mineru-api:8000` |
| PostgreSQL | `db_postgres:5432` |
| Redis | `redis:6379` |

Der Host-Port ist in `compose.yaml` an `127.0.0.1` gebunden. Die
Weboberflächen sind deshalb nur auf dem Docker-Host unter
`http://localhost:8080` erreichbar. Die Anwendung besitzt keine Anmeldung und
darf nicht öffentlich bereitgestellt werden.

Dify erreicht das Backend innerhalb des gemeinsamen Docker-Netzwerks. Sein
SSRF-Proxy darf gezielt den internen Namen freigeben:

```env
SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=application-assistant-backend
```

Eine pauschale Freigabe privater Netzbereiche ist nicht erforderlich.

## Konfiguration

Lokale Einstellungen liegen in der ignorierten `.env`:

```powershell
Copy-Item .env.example .env
```

Wichtige Variablen:

| Variable | Standard | Bedeutung |
|---|---|---|
| `APP_ENV` | `development` | deaktiviert in `production` Swagger und ReDoc |
| `APP_PORT` | `8080` | Port auf dem Docker-Host |
| `APP_LOG_LEVEL` | `INFO` | Log-Level |
| `DATABASE_URL` | leer | Datenbankverbindung der Kernanwendung |
| `REDIS_URL` | leer | Redis-Verbindung |
| `DIFY_BASE_URL` | `http://api:5001` | interne Dify-API |
| `DIFY_CV_WORKFLOW_API_KEY` | leer | Legacy-CV-Import-Workflow |
| `DIFY_CV_RECOMMENDER_WORKFLOW_API_KEY` | leer | verÃ¶ffentlichter CV-Recommender |
| `DIFY_MATCHING_WORKFLOW_API_KEY` | leer | Matching-Workflow |
| `DIFY_METADATA_WORKFLOW_API_KEY` | leer | Metadaten-Fallback |
| `MINERU_BASE_URL` | `http://mineru-api:8000` | MinerU-API |
| `APPLICATION_DOCUMENTS_PATH` | `/app/data/application-documents` | archivierte PDFs |

Passwörter und API-Schlüssel gehören ausschließlich in `.env`, niemals in
Git, Workflow-DSLs oder Browser-Code.

### Reviewer / Review-Workflows

Optional kann die Anwendung Extraktions- und Matching-Reviews an externe
Dify-Workflows auslagern. Reviews laufen asynchron und sind so gestaltet,
dass fehlgeschlagene oder fehlerhafte Reviews Import- oder Matchingvorgänge
nicht abbrechen. Stattdessen werden alle Review-Versuche in der Review-
Historie protokolliert (`review_runs`, `review_issues`).

- Konfiguration erfolgt über die lokale `.env`-Variable `REVIEW_WORKFLOWS`
  (JSON-Mapping mit Dify-App-API-Keys als Schlüssel). Beispiel:

  ```text
  REVIEW_WORKFLOWS='{"app-abc123": {"enabled": true, "api_key": "app-abc123"}}'
  ```

- Wichtig: `workflow_id` wird in den Payloads nicht mehr benötigt. Dify-
  Workflows erwarten das Feld `attempt` als Text/String; numerische Werte
  führen zu Fehlern in der DSL. API-Schlüssel und Workflow-Versionen sollten
  nach dem Import überprüft werden.

## Datenhaltung

Die Anwendung verwendet eine eigene PostgreSQL-Datenbank. Dify-Datenbanken und
-Tabellen werden nicht verändert. Ausstehende Migrationen laufen beim
Containerstart automatisch; manuell:

```powershell
docker compose run --rm application-assistant-backend alembic upgrade head
```

Kanonisch gespeichert werden unter anderem:

- Profile, Skills, Berufserfahrung, Ausbildung und Zertifikate
- versionierte Master-Profile, CV-Empfehlungen und generierte CV-Dokumente
- Stellen, Anforderungen und strukturierte Metadaten
- profilspezifische Matchings und Evidenzzuordnungen
- Bewerbungen und Verlaufsereignisse
- Metadaten archivierter Bewerbungsunterlagen

Archivierte PDFs liegen im Docker-Volume `application-documents`, nicht als
Binärdaten in PostgreSQL. Datenbank und Volume müssen gemeinsam gesichert
werden.

## Importpipeline

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

URL-Importe akzeptieren nur öffentliche HTTP(S)-Ziele. Private, lokale und
reservierte Adressen sowie eingebettete Zugangsdaten werden blockiert.
Redirects und Browser-Subrequests werden erneut geprüft.

PDFs werden zunächst nativ gelesen. Unzureichende oder beschädigte Text-Layer
lösen MinerU aus; bei eindeutig defekten Glyphen werden Seiten zuvor
gerastert. HTML/SingleFile wird lokal bereinigt und lädt keine externen
Ressourcen nach.

## Profil und Matching

CV-Importe erzeugen prüfbare Vorschläge und überschreiben das kanonische
Profil nicht automatisch. Änderungen an Profilentitäten erzeugen
Revisionssnapshots.

Matching verwendet belegte Skills, Berufserfahrung, Portfolio-Projekte,
Ausbildung und Zertifikate. Berufliche, projektbezogene, schulische und
Trainingskontexte
bleiben unterscheidbar. Referenzen und Kontaktdaten werden nicht als
Matching-Evidenz an Dify übergeben. Seniority-Anforderungen aus der
Stellenanzeige werden separat gegen die Berufserfahrung im Profil bewertet und
fließen als eigener Teilbefund in das Ergebnis ein.

Der davon getrennte Ziel-Fit verwendet die strukturierten Zielpräferenzen des
Profils. Beschäftigungsarten haben dabei Gewicht 30 und berücksichtigen bei
einer befristeten Anstellung zusätzlich die hinterlegte Mindestlaufzeit in
Monaten.

Jeder erneute Import derselben Stelle (Reimport, PDF-Ersatz) schreibt einen
Änderungssatz in den Job-Aktivitätsverlauf. Archivierte Jobs bleiben erhalten,
werden aber standardmäßig aus aktiven Listen ausgeblendet und können
wiederhergestellt werden.

Portfolio-Projekte sind als eigene, prüfbare Evidenzquelle umgesetzt;
persönliche Ziele sind strukturiert am Profil erfasst. Der aktuelle Stand und
die Evaluationsstrategie stehen in der
[Roadmap](roadmap.md) und in [Evaluation](evaluation.md).

## Bewerbungsverlauf und Dokumente

Die CV-Vorlage wird auf der Job-/Bewerbungsdetailseite aus Jobkontext und
Master-Profil erzeugt. Dify liefert nur die strukturierte Empfehlung; die
Auswahl-IDs werden im Backend gegen das Master-Profil geprüft. Das Backend
rendert das CV-Markdown deterministisch und speichert Neugenerierungen als
neue Version mit Master-Profil- und Empfehlungs-Provenienz. Referenzen sind
optional; Aktivitäts-Bullets werden in der Verwaltung gepflegt.

Eine Bewerbung gehört zu genau einem Job und Profil. Statuswechsel und
Kommunikation werden als Ereignisse gespeichert. Ereignisse können bearbeitet
oder gelöscht werden; danach wird der Bewerbungszustand aus den verbleibenden
Ereignissen neu aufgebaut.

Quellportal und tatsächlicher Bewerbungsweg sind getrennte Angaben. Bei einem
Jobportal kann dessen Name, beispielsweise LinkedIn oder Indeed, erfasst
werden.

## Upgrade-Grenzen

- Datenbankschemaänderungen erfolgen ausschließlich über Alembic.
- Workflow-DSLs werden versioniert exportiert und manuell in Dify importiert.
- Dify- und MinerU-Upgrades bleiben außerhalb der Kernanwendung, solange ihre
  HTTP-Verträge kompatibel sind.
- Neue Workflow-Versionen ersetzen keine veröffentlichte Dify-App automatisch.
