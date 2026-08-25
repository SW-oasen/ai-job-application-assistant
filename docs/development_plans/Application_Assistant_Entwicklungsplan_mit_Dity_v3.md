# Application Assistant – Entwicklungsplan und MinerU-Konfiguration

Stand: 21.07.2026  
Zielgruppe: Codex / Entwickler  
Status: Planungsgrundlage für die nächste Umsetzungsphase

---

## 1. Ziel des Projekts

Der Application Assistant soll Bewerbungen nicht nur textuell unterstützen, sondern als dauerhaft nutzbare lokale Anwendung strukturieren und verwalten.

Die Anwendung soll schrittweise folgende Aufgaben übernehmen:

1. Stellenanzeigen aus URLs, PDFs oder eingefügtem Text importieren.
2. Stelleninformationen strukturiert extrahieren.
3. Bewerbungen, Unternehmen, Anforderungen und erzeugte Dokumente verwalten.
4. Stellenanforderungen mit dem eigenen Profil und Portfolio abgleichen.
5. geeignete Projekte und Erfahrungen empfehlen.
6. Lebenslauf und Anschreiben vorbereiten.
7. später Interviewvorbereitung und Bewerbungsstatus ergänzen.

Portfolio-Tauglichkeit ist ein Nebeneffekt. Vorrangig ist ein zuverlässiges Werkzeug für den eigenen Bewerbungsprozess.

---

## 2. Architekturprinzipien

### 2.1 Verantwortlichkeiten trennen

```text
Dify
├── Workflow-Orchestrierung
├── LLM-Aufrufe
├── Prompt-Verwaltung
├── einfache Verzweigungen
└── kleine Code-Nodes

Python-Backend
├── Webseitenimport
├── PDF-Importsteuerung
├── Datenbereinigung
├── Geschäftslogik
├── Datenbankzugriffe
├── Validierung
├── Fehlerbehandlung
└── Tests

PostgreSQL
├── strukturierte Stellen- und Bewerbungsdaten
├── Firmeninformationen
├── Anforderungs-Matches
└── Dokumentversionen

ChromaDB / RAG
├── Lebenslauftexte
├── Projektbeschreibungen
├── Zeugnisse
├── Lern- und Erfahrungsnotizen
└── längere unstrukturierte Inhalte

MinerU
└── OCR- und Layout-Fallback für bildbasierte PDFs
```

### 2.2 Dify ist Orchestrator, nicht Haupt-Backend

Dify-Code-Nodes sollen nur kleine, übersichtliche Aufgaben enthalten, zum Beispiel:

- Textlänge prüfen
- URLs validieren
- JSON-Felder umformen
- Fallback-Flags setzen
- Pflichtfelder prüfen
- einfache Confidence-Werte berechnen

Größere Logik gehört in versionierte Python-Module.

### 2.3 Originaldaten erhalten

Für jede importierte Stelle sollen neben den extrahierten Daten auch die Rohdaten gespeichert werden:

- Original-URL
- Roh-HTML oder bereinigtes Markdown
- Original-PDF, sofern vorhanden
- MinerU-Ausgabe, sofern verwendet
- extrahiertes JSON
- Prompt-Version
- Importzeitpunkt

Dadurch kann eine Anzeige später mit verbesserten Prompts erneut verarbeitet werden.

---

## 3. Zielarchitektur

```text
Benutzer
   │
   ├── URL
   ├── PDF
   └── eingefügter Text
   │
   ▼
Dify Workflow
   │
   ├── HTTP Request an Python-Backend
   ├── LLM-Extraktion
   ├── Matching
   └── Dokumenterzeugung
   │
   ▼
FastAPI Backend
   │
   ├── URL Importer
   │     ├── einfacher HTTP-Import
   │     └── Playwright-Fallback
   │
   ├── PDF Importer
   │     ├── Text-PDF
   │     └── MinerU-Fallback
   │
   ├── Normalisierung
   ├── Validierung
   └── PostgreSQL
   │
   ▼
PostgreSQL + ChromaDB
```

---

## 4. Vorgeschlagene Projektstruktur

```text
application-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── health.py
│   │   │   ├── imports.py
│   │   │   ├── jobs.py
│   │   │   └── applications.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── exceptions.py
│   │   ├── importers/
│   │   │   ├── base.py
│   │   │   ├── url_importer.py
│   │   │   ├── http_importer.py
│   │   │   ├── playwright_importer.py
│   │   │   ├── pdf_importer.py
│   │   │   └── mineru_client.py
│   │   ├── parsers/
│   │   │   ├── html_to_markdown.py
│   │   │   ├── text_quality.py
│   │   │   └── source_detection.py
│   │   ├── services/
│   │   │   ├── job_import_service.py
│   │   │   ├── job_service.py
│   │   │   └── application_service.py
│   │   ├── database/
│   │   │   ├── session.py
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── migrations/
│   │   └── schemas/
│   │       ├── import_schema.py
│   │       ├── job_schema.py
│   │       └── application_schema.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
│
├── dify/
│   ├── workflows/
│   ├── prompts/
│   ├── schemas/
│   └── README.md
│
├── docs/
│   ├── architecture.md
│   ├── mineru-setup.md
│   ├── api.md
│   └── decisions/
│
├── data/
│   ├── samples/
│   └── .gitkeep
│
├── docker-compose.yml
├── README.md
└── .gitignore
```

---

## 5. Entwicklungsphasen

# Phase 1 – Projektbasis und Backend-Grundgerüst

## Ziel

Ein kleines, lokal ausführbares FastAPI-Backend, das Dify per HTTP aufrufen kann.

## Aufgaben

- FastAPI-Projekt initialisieren.
- Konfiguration über `.env` einführen.
- Logging einrichten.
- Fehlerantworten vereinheitlichen.
- Health-Endpunkt erstellen.
- Dockerfile für das Backend ergänzen.
- optional in bestehendes Docker-Netzwerk von Dify einbinden.

## Endpunkte

### `GET /health`

Beispielantwort:

```json
{
  "status": "ok",
  "service": "application-assistant-backend",
  "version": "0.1.0"
}
```

### Akzeptanzkriterien

- Backend startet lokal.
- `GET /health` liefert HTTP 200.
- Dify kann den Endpunkt per HTTP-Request-Node erreichen.
- Konfiguration enthält keine fest codierten lokalen Pfade oder Zugangsdaten.

---

# Phase 2 – URL-Import MVP

## Ziel

Eine Stellenanzeige per URL laden und als bereinigten Text beziehungsweise Markdown an Dify zurückgeben.

## Importstrategie

```text
URL
 ↓
URL validieren
 ↓
einfacher HTTP-Abruf
 ↓
Inhalt ausreichend?
 ├── Ja → HTML bereinigen
 └── Nein → Playwright-Fallback
 ↓
Markdown/Text erzeugen
 ↓
Metadaten zurückgeben
```

## Aufgaben

- URL-Schema auf `http` und `https` begrenzen.
- private Netzwerkziele und lokale Adressen standardmäßig blockieren.
- Timeouts und maximale Downloadgröße definieren.
- einfachen HTTP-Importer implementieren.
- HTML mit BeautifulSoup oder selectolax parsen.
- störende Elemente entfernen:
  - `script`
  - `style`
  - `svg`
  - Navigation
  - Footer
  - Cookie-Hinweise, soweit erkennbar
- Hauptinhalt bevorzugen:
  - `main`
  - `article`
  - strukturierte Job-Markups
- HTML in Markdown oder sauberen Text umwandeln.
- Qualitätsprüfung implementieren.
- Playwright als Fallback ergänzen.

## Qualitätsmerkmale

Ein Import gilt zunächst als brauchbar, wenn:

- mindestens 500 sinnvolle Zeichen vorhanden sind,
- ein Titel oder eine Überschrift erkannt wird,
- der Text nicht überwiegend aus Navigation besteht,
- keine offensichtliche Login- oder Bot-Schutzseite geliefert wurde.

Diese Regeln sollen konfigurierbar bleiben.

## API

### `POST /imports/url`

Request:

```json
{
  "url": "https://example.com/job/123",
  "force_browser": false
}
```

Response:

```json
{
  "success": true,
  "source_type": "url",
  "source_url": "https://example.com/job/123",
  "retrieval_method": "http",
  "title": "Data Engineer",
  "raw_html": "<html>...</html>",
  "markdown": "# Data Engineer\n...",
  "text_length": 8421,
  "warnings": []
}
```

## Playwright-Regeln

Playwright nur verwenden, wenn:

- HTTP-Abruf zu wenig Inhalt liefert,
- JavaScript erforderlich ist,
- relevante Inhalte dynamisch nachgeladen werden,
- der Benutzer `force_browser=true` setzt.

Keine automatische Umgehung von Login, Paywall, CAPTCHA oder Bot-Schutz implementieren.

## Akzeptanzkriterien

- mindestens drei unterschiedliche Karrierewebseiten erfolgreich importieren,
- mindestens eine JavaScript-Seite über Playwright importieren,
- Importfehler liefern verständliche Fehlermeldungen,
- Roh-HTML und bereinigtes Markdown bleiben getrennt.

---

# Phase 3 – Dify-Workflow „Import Job from URL“

## Ziel

Dify ruft das Backend auf und extrahiert aus dem gelieferten Markdown ein strukturiertes Stellenprofil.

## Workflow

```text
Start
  └── job_url
       ↓
HTTP Request
  POST /imports/url
       ↓
Code Node
  Qualitäts- und Fehlerprüfung
       ↓
LLM
  Stellenextraktion
       ↓
Structured Output
       ↓
End
```

## Dify-Code-Node

Nur kleine Prüfungen:

- `success == true`
- Mindestlänge
- leeres Markdown erkennen
- Warnungen zusammenfassen
- `needs_manual_review` setzen

## Extraktionsfelder

Mindestens:

- Jobtitel
- Unternehmen
- Standort
- Arbeitsmodell
- Beschäftigungsart
- Aufgaben
- Muss-Anforderungen
- Kann-Anforderungen
- Technologien
- Ausbildung
- Berufserfahrung
- Sprachen
- Benefits
- Gehalt, sofern genannt
- Ansprechpartner
- Bewerbungsfrist
- Belegstellen beziehungsweise Evidence
- Unsicherheiten

## Akzeptanzkriterien

- URL-Eingabe erzeugt valides JSON.
- Fehlende Informationen werden `null` oder als leere Liste ausgegeben.
- Arbeitgeberinformationen und Portalnavigation werden nicht mit Anforderungen verwechselt.
- Sprache wird aus dem eigentlichen Stelleninhalt bestimmt.

---

# Phase 4 – PDF-Import mit MinerU-Fallback

## Ziel

Textuelle und bildbasierte PDFs zuverlässig verarbeiten.

## Strategie

```text
PDF
 ↓
normaler Text-Extractor
 ↓
Textqualität prüfen
 ├── ausreichend → direkt weiter
 └── unzureichend → MinerU
 ↓
Markdown
 ↓
Stellenextraktion
```

## Aufgaben

- PDF-Upload im Backend oder zunächst über Dify unterstützen.
- Textmenge und Textqualität prüfen.
- MinerU-Client implementieren.
- Timeouts für große OCR-Aufgaben deutlich höher setzen.
- MinerU-Fehler verständlich weitergeben.
- Original-PDF und MinerU-Ergebnis getrennt speichern.
- optional asynchronen MinerU-Endpunkt später ergänzen.

## API

### `POST /imports/pdf`

Multipart-Upload:

```text
file=<job.pdf>
```

Beispielantwort:

```json
{
  "success": true,
  "source_type": "pdf",
  "extraction_method": "mineru",
  "markdown": "# Data Scientist\n...",
  "text_length": 6940,
  "warnings": []
}
```

## Akzeptanzkriterien

- textuelles PDF wird ohne MinerU verarbeitet,
- bildbasiertes PDF wird über MinerU verarbeitet,
- OCR-Fallback wird nur bei Bedarf gestartet,
- identische Datei wird nicht mehrfach unnötig verarbeitet.

---

# Phase 5 – PostgreSQL-Datenmodell

## Ziel

Stellen und Bewerbungen dauerhaft und nachvollziehbar verwalten.

## Erste Tabellen

### `companies`

- `id`
- `name`
- `website`
- `industry`
- `description`
- `location`
- `created_at`
- `updated_at`

### `jobs`

- `id`
- `company_id`
- `title`
- `source_url`
- `source_portal`
- `location`
- `work_model`
- `employment_type`
- `language`
- `status`
- `published_at`
- `deadline`
- `imported_at`
- `raw_content`
- `normalized_content`
- `extracted_json`
- `prompt_version`
- `content_hash`

### `job_requirements`

- `id`
- `job_id`
- `category`
- `requirement_text`
- `normalized_value`
- `priority`
- `evidence`
- `confidence`

### `applications`

- `id`
- `job_id`
- `status`
- `applied_at`
- `next_action`
- `next_action_at`
- `notes`
- `created_at`
- `updated_at`

### `generated_documents`

- `id`
- `application_id`
- `document_type`
- `language`
- `version`
- `content`
- `prompt_version`
- `created_at`

### `requirement_matches`

- `id`
- `job_requirement_id`
- `profile_source`
- `match_level`
- `evidence`
- `gap`
- `confidence`

## Statuswerte

Beispiel:

```text
saved
analyzing
planned
drafting
applied
interview
rejected
withdrawn
offer
archived
```

## Akzeptanzkriterien

- Migrationen sind reproduzierbar.
- importierte Stelle kann erneut geladen werden.
- doppelte URL oder identischer Content-Hash wird erkannt.
- Änderungen an Extraktion überschreiben nicht unbemerkt alte Dokumentversionen.

---

# Phase 6 – Profil- und Portfolio-Matching

## Ziel

Anforderungen gegen reale Erfahrungen abgleichen, ohne Fähigkeiten zu erfinden.

## Datenquellen

- strukturierte Skills aus PostgreSQL,
- Lebenslauf,
- Projektbeschreibungen,
- GitHub-README-Texte,
- Zeugnisse,
- Interview- und Lernnotizen aus RAG.

## Ergebnis

Pro Anforderung:

```json
{
  "requirement": "Production experience with AWS",
  "match_level": "gap",
  "evidence": [],
  "explanation": "Only exercise-level cloud experience is documented.",
  "recommended_action": "Do not claim production experience."
}
```

## Match-Level

- `strong_match`
- `partial_match`
- `transferable`
- `gap`
- `unknown`

## Akzeptanzkriterien

- jedes positive Match enthält Evidence,
- fehlende Berufserfahrung wird nicht durch Projektarbeit ersetzt, sondern klar unterschieden,
- Empfehlungen benennen sinnvolle Portfolio-Projekte,
- kritische Lücken werden sichtbar dargestellt.

---

# Phase 7 – Bewerbungsdokumente

## Ziel

Aus Stellenprofil und Matching kontrolliert Dokumententwürfe erzeugen.

## Reihenfolge

1. Profilzusammenfassung
2. CV-Anpassungsvorschläge
3. Projektauswahl
4. Anschreiben
5. kurze Bewerbungsfragen
6. Interviewvorbereitung

## Regeln

- Fakten nur aus freigegebenen Profilquellen.
- Keine erfundene Berufserfahrung.
- Projekt- und Trainingserfahrung eindeutig kennzeichnen.
- Jede Ausgabe versionieren.
- Sprache der Anzeige berücksichtigen.
- alte Versionen nicht überschreiben.

---

## 6. Kleine Code-Nodes versus Backend-Code

### Geeignet für Dify-Code-Nodes

- Textlänge prüfen
- boolesche Flags setzen
- JSON-Schlüssel umbenennen
- leere Werte normalisieren
- Listen zusammenführen
- Confidence begrenzen
- Routing vorbereiten

### Nicht für Dify-Code-Nodes geeignet

- Playwright
- umfangreiches Scraping
- Datenbankzugriffe mit mehreren Tabellen
- komplexes Matching
- Wiederholungslogik
- MinerU-Client mit Datei-Uploads
- portalabhängige Parser
- umfangreiche Fehlerbehandlung
- wiederverwendbare Geschäftslogik

Richtwert: Wenn ein Code-Node deutlich über etwa 30–50 Zeilen wächst oder Tests benötigt, soll die Logik in das Backend verschoben werden.

---

## 7. Sicherheits- und Robustheitsanforderungen

### URL-Import

- nur `http` und `https`,
- lokale und private IP-Bereiche standardmäßig blockieren,
- Weiterleitungen erneut prüfen,
- maximale Dateigröße begrenzen,
- Request-Timeout,
- User-Agent setzen,
- keine Zugangsdaten in Logs,
- keine automatische CAPTCHA-Umgehung.

### Datei-Import

- erlaubte MIME-Typen prüfen,
- maximale Dateigröße definieren,
- Dateinamen normalisieren,
- Content-Hash erzeugen,
- temporäre Dateien sicher löschen,
- OCR nur bei Bedarf starten.

### LLM-Ausgaben

- JSON-Schema validieren,
- fehlerhafte Ausgabe nicht direkt speichern,
- Prompt-Version protokollieren,
- Evidence-Felder verpflichtend machen,
- manuelle Prüfung ermöglichen.

---

## 8. Teststrategie

### Unit-Tests

- URL-Validierung
- Textqualitätsprüfung
- HTML-Bereinigung
- Source Detection
- Content-Hash
- Mapping von Statuswerten
- MinerU-Response-Parser

### Integrationstests

- FastAPI + PostgreSQL
- FastAPI + MinerU
- FastAPI + Playwright
- Dify + FastAPI
- vollständiger URL-Import
- vollständiger Image-PDF-Import

### Test-Fixtures

Mindestens:

- einfache statische Karriereseite,
- JavaScript-lastige Stellenanzeige,
- textuelles PDF,
- bildbasiertes PDF,
- leere beziehungsweise blockierte Webseite,
- abgelaufene Stellenanzeige,
- Seite mit viel Portalnavigation.

---

## 9. Logging und Nachvollziehbarkeit

Jeder Import soll mindestens protokollieren:

- Request-ID
- Quelle
- Importmethode
- Dauer
- Content-Länge
- verwendeter Fallback
- Warnungen
- Fehlerklasse
- MinerU-Task-ID, sofern vorhanden
- gespeicherter Job-Datensatz

Keine vollständigen Bewerbungsunterlagen oder personenbezogenen Inhalte in normalen Logs speichern.

---

## 10. Priorisierte Umsetzung für Codex

### Sprint 1

- Projektstruktur anlegen
- FastAPI initialisieren
- `/health`
- Konfiguration
- Logging
- Tests
- Dockerfile

### Sprint 2

- `/imports/url`
- einfacher HTTP-Importer
- HTML-Bereinigung
- Markdown-Ausgabe
- Qualitätsprüfung
- Unit-Tests

### Sprint 3

- Playwright-Fallback
- Fehlerklassen
- Dify-Workflow anbinden
- drei reale Stellenanzeigen testen

### Sprint 4

- MinerU-Client
- `/imports/pdf`
- Text-PDF-Erkennung
- MinerU-Fallback
- zwei PDF-Testfälle

### Sprint 5

- PostgreSQL
- Alembic
- Kernmodelle
- Import speichern
- Dublettenprüfung

### Sprint 6

- Profil- und Requirement-Matching
- Evidence-Verknüpfung
- erste Dokumentversionierung

Codex soll pro Sprint kleine, prüfbare Änderungen umsetzen und nach jedem Sprint Tests ausführen.

