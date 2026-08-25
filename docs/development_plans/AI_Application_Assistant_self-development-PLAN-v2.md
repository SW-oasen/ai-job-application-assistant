# Projektplan: AI Application Assistant

## 1. Projektziel

Der **AI Application Assistant** ist eine lokale, modular aufgebaute Anwendung zur Verwaltung und Unterstützung des gesamten Bewerbungsprozesses.

Die Anwendung soll nicht versuchen, einen allgemeinen Chat-Assistenten nachzubauen. Ihr Kernnutzen liegt in der **Automatisierung und Orchestrierung wiederkehrender Bewerbungsabläufe**:

- interessante Stellen regelmäßig finden,
- Stellenanzeigen strukturiert erfassen,
- Passung zum eigenen Profil analysieren,
- Bewerbungen und ihre Zustände verwalten,
- Aufgaben und Fristen verfolgen,
- Anschreiben und Profiltexte als überprüfbare Entwürfe erzeugen,
- alle Vorgänge in einem Dashboard übersichtlich darstellen.

Der Mensch bleibt bei allen wichtigen Entscheidungen verantwortlich. Bewerbungen und Nachrichten werden nicht automatisch versendet.

## 2. Abgrenzung

### Die Anwendung ist

- Bewerbungsverwaltungssystem
- Job-Monitoring-System
- Workflow-Orchestrator
- lokaler AI-Assistent
- RAG-Anwendung
- Analyse- und Dashboard-Anwendung

### Die Anwendung ist nicht

- autonomer Bewerbungsbot
- vollautomatisches Versandwerkzeug
- allgemeiner ChatGPT-Ersatz
- System zur Erfindung oder Ausschmückung von Erfahrungen
- Scraper ohne Rücksicht auf robots.txt, Nutzungsbedingungen oder technische Grenzen

## 3. Hauptfunktionen

### 3.1 Bewerbungsverwaltung

Jede Bewerbung wird als eigener Vorgang gespeichert.

Mögliche Statuswerte:

```text
DISCOVERED
REVIEWING
INTERESTING
PREPARING
READY_TO_APPLY
APPLIED
CONFIRMATION_RECEIVED
INTERVIEW
OFFER
REJECTED
WITHDRAWN
ARCHIVED
```

Zu jedem Vorgang werden mindestens gespeichert:

- Unternehmen
- Stellenbezeichnung
- Standort
- Quelle
- URL
- Veröffentlichungsdatum
- Erfassungsdatum
- Bewerbungsstatus
- Match-Bewertung
- Ansprechpartner
- Gehaltsvorstellung
- Eintrittstermin
- verwendete CV-Version
- verwendete Anschreibenversion
- nächste Aktion
- Frist
- Notizen

Zusätzlich wird jede Statusänderung in einer Historie protokolliert.

### 3.2 Aufgabenverwaltung

Zu Bewerbungen können Aufgaben angelegt werden.

Beispiele:

- Stelle prüfen
- Lebenslauf anpassen
- Anschreiben erstellen
- Ansprechpartner recherchieren
- Bewerbung versenden
- nachfassen
- Interview vorbereiten
- Rückmeldung dokumentieren

Eine Aufgabe besitzt mindestens:

```text
id
application_id
title
task_type
priority
status
due_date
created_at
completed_at
notes
```

### 3.3 Job Watcher

Der Job Watcher kontrolliert definierte Karriereseiten regelmäßig.

Er soll:

- gespeicherte Suchseiten abrufen,
- Stellenlinks erkennen,
- neue Stellen von bereits bekannten Stellen unterscheiden,
- geänderte Stellen markieren,
- entfernte Stellen erkennen,
- die Ergebnisse strukturiert speichern,
- keine Bewerbung automatisch auslösen.

Beispiel einer konfigurierten Suchquelle:

```text
https://www.capgemini.com/de-de/karriere/jobs/?page=2&size=11&professional_communities=Business+Analysis&experience_level=Berufserfahrene%2CAbsolvent*innen&location=Berlin&country_code=de-de
```

Die URL-Parameter sollen nicht fest im Code stehen, sondern als konfigurierbare Quelle gespeichert werden.

### 3.4 Stellenanalyse

Eine Stellenanzeige kann geladen werden über:

- manuell eingefügten Text
- PDF
- gespeicherte Webseite
- Job-Watcher-Ergebnis

Die Analyse extrahiert:

- Zielrolle
- Senioritätslevel
- Unternehmen
- Branche
- Standort
- Arbeitsmodell
- Aufgaben
- Muss-Anforderungen
- Kann-Anforderungen
- Technologien
- Soft Skills
- Sprachkenntnisse
- Gehaltsangaben
- Ansprechpartner
- Bewerbungsfrist
- relevante Keywords

Das Ergebnis wird als validierbares JSON gespeichert.

### 3.5 Profil-Matching

Die Stellenanforderungen werden mit der privaten Bewerbungsbibliothek verglichen.

Bewertung je Anforderung:

```text
STRONG_MATCH
PARTIAL_MATCH
MISSING
UNCERTAIN
```

Zusätzlich:

- Gesamtbewertung
- zentrale Stärken
- fehlende Kenntnisse
- übertragbare Erfahrungen
- Bewerbungsrisiken
- empfohlene Positionierung
- empfohlene Projekte
- empfohlene CV-Version
- empfohlene Anschreibenstrategie

Das Matching ist eine Entscheidungshilfe, keine automatische Bewerbungsentscheidung.

### 3.6 Dokumentenassistent

Der Dokumentenassistent erstellt überprüfbare Entwürfe für:

- Anschreiben
- Profiltext im Lebenslauf
- Skill-Reihenfolge
- kurze Bewerbungs-E-Mail
- Follow-up-E-Mail
- Interviewvorbereitung
- Zusammenfassung der Stellenanforderungen

Regeln:

- nur belegbare Informationen verwenden
- keine erfundenen Erfahrungen
- keine erfundenen Technologien
- keine Übertreibungen
- Quellenmodule anzeigen
- menschliche Prüfung erzwingen
- keine automatische Versendung

### 3.7 Dashboard

Das Dashboard zeigt mindestens:

#### Kennzahlen

- neue Stellen
- offene Bewerbungen
- fällige Aufgaben
- Bewerbungen ohne Rückmeldung
- Interviews
- Antwortquote

#### Ansichten

- Kanban-Board nach Bewerbungsstatus
- Aufgabenliste
- neue Stellen aus Watchlists
- Bewerbungen mit nahender Frist
- Bewerbungen ohne Rückmeldung
- letzte Statusänderungen

#### Spätere Analysen

- Antwortquote nach Rollenart
- Antwortquote nach CV-Version
- häufig verlangte Technologien
- häufig fehlende Skills
- durchschnittliche Zeit bis zur Rückmeldung
- erfolgreichste Jobquellen

## 4. Datenschutz und Veröffentlichungsstrategie

### Private Daten

Nicht ins öffentliche Repository:

- echte Bewerbungsunterlagen
- Lebenslauf
- Zeugnisse
- private Bewerbungsbibliothek
- Bewerbungsstatus
- Unternehmensnotizen
- echte Stellen-Snapshots
- E-Mail-Inhalte
- Zugangsdaten
- API-Schlüssel

### Öffentliches Repository

Veröffentlicht werden dürfen:

- Quellcode
- Dummy-Daten
- Beispieldokumente
- Architektur
- Datenbankschema
- Beispiel-Workflows
- README
- Screenshots mit anonymisierten Daten
- Demo-Konfigurationen

### Sicherheitsregeln

- Secrets ausschließlich über Environment-Variablen
- `.env` niemals committen
- private Datenverzeichnisse in `.gitignore`
- Logs dürfen keine sensiblen Dokumentinhalte enthalten
- Löschfunktion für gespeicherte Stellen und Bewerbungen
- lokale Verarbeitung bevorzugen

## 5. Empfohlene Architektur

```text
Frontend
React + TypeScript
        |
        v
Backend API
FastAPI
        |
        +-----------------------------+
        |                             |
        v                             v
PostgreSQL                    AI Services
operative Daten               Job Analyzer
Statushistorie                Matcher
Tasks                         Document Generator
Watchlists                    RAG Retriever
        |
        v
Background Jobs
Scheduler / Worker
        |
        v
Source Adapters
HTML / Playwright / APIs
```

### Ergänzende Komponenten

```text
Vector Store:
ChromaDB oder pgvector

LLM:
lokales Modell über Ollama
optional austauschbarer Cloud-Provider

Embeddings:
lokales Embedding-Modell

Dateispeicher:
lokales privates Verzeichnis

Export:
Markdown zuerst
später DOCX und PDF
```

## 6. Technologieentscheidung

### Backend

- Python 3.13
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- pytest

### Frontend

- React
- TypeScript
- Vite
- React Router
- TanStack Query
- einfache UI-Komponenten ohne unnötig großes Framework

### Scraping

Reihenfolge der bevorzugten Methoden:

1. öffentliche API oder strukturierte JSON-Daten
2. serverseitig geliefertes HTML
3. eingebettete strukturierte Daten
4. Playwright nur für JavaScript-abhängige Seiten

Bibliotheken:

- httpx
- BeautifulSoup
- Playwright
- selectolax optional

### Hintergrundprozesse

Für MVP:

- APScheduler oder einfacher interner Scheduler

Später bei Bedarf:

- Celery oder Dramatiq
- Redis

### AI/RAG

- Ollama
- austauschbare LLM-Abstraktion
- sentence-transformers
- ChromaDB oder pgvector

## 7. Datenmodell

### Kernentitäten

```text
users
companies
contacts
job_sources
job_postings
job_posting_snapshots
applications
application_status_history
tasks
documents
document_versions
profile_modules
job_analyses
match_results
watch_runs
notifications
```

### Minimales Schema für MVP

#### companies

```text
id
name
website
notes
created_at
updated_at
```

#### job_sources

```text
id
company_id
name
source_type
base_url
search_url
is_active
check_interval_hours
last_checked_at
created_at
updated_at
```

#### job_postings

```text
id
source_id
external_id
company_id
title
location
url
published_at
first_seen_at
last_seen_at
content_hash
is_active
raw_text
created_at
updated_at
```

#### applications

```text
id
job_posting_id
status
match_score
salary_expectation
available_from
contact_id
cv_version
cover_letter_version
next_action
next_action_due_at
notes
applied_at
created_at
updated_at
```

#### application_status_history

```text
id
application_id
old_status
new_status
changed_at
note
```

#### tasks

```text
id
application_id
title
task_type
priority
status
due_date
completed_at
notes
created_at
updated_at
```

#### job_analyses

```text
id
job_posting_id
analysis_version
language
target_role
seniority
industry
responsibilities_json
required_skills_json
preferred_skills_json
soft_skills_json
keywords_json
raw_result_json
created_at
```

#### match_results

```text
id
job_posting_id
profile_version
overall_score
overall_rating
strengths_json
gaps_json
risks_json
recommended_projects_json
recommended_strategy
raw_result_json
created_at
```

## 8. Private Bewerbungsbibliothek

Die vorhandene modulare Bibliothek bleibt erhalten, wird aber um strukturierte Fakten ergänzt.

```text
application_library/

├── Master/
├── Profile/
├── Projects/
├── Experience/
├── Position/
├── Company/
├── Skills/
└── Evidence/
```

### Neue Kategorien

#### Skills

Einzelne nachweisbare Kompetenzen:

```text
Java
Spring Boot
Python
SQL
PostgreSQL
Docker
RAG
Forecasting
Power BI
```

#### Evidence

Belege und Herkunft einer Aussage:

- Berufserfahrung
- Projekt
- Weiterbildung
- Zertifikat
- Zeugnis
- Portfolio-Link

Damit kann die Anwendung unterscheiden zwischen:

```text
Kenntnis vorhanden
praktisch im Projekt verwendet
beruflich eingesetzt
nur aktuell in Einarbeitung
```

## 9. Human-in-the-Loop-Regeln

### Automatisch erlaubt

- Watchlist prüfen
- Stellen speichern
- Duplikate erkennen
- Stellenänderungen erkennen
- Anforderungen extrahieren
- Aufgaben vorschlagen
- Erinnerungen berechnen

### Nur nach Bestätigung

- Bewerbungsvorgang anlegen
- Status verändern
- Match-Ergebnis übernehmen
- Anschreiben speichern
- Profiltext speichern
- Aufgabe als erledigt markieren

### Nur manuell

- Bewerbung absenden
- E-Mail absenden
- externe Formulare ausfüllen
- endgültige Absageentscheidung
- private Dokumente veröffentlichen
- personenbezogene Daten ändern

## 10. Projektstruktur

```text
ai-application-assistant/

├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── api/
│   │   ├── ai/
│   │   ├── scraping/
│   │   ├── scheduler/
│   │   └── prompts/
│   ├── tests/
│   ├── alembic/
│   └── pyproject.toml
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   ├── pages/
│   │   ├── types/
│   │   └── main.tsx
│   └── package.json
│
├── example_library/
├── docs/
│   ├── architecture.md
│   ├── data_model.md
│   ├── scraping_rules.md
│   └── privacy.md
│
├── docker/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── PLAN.md
```

## 11. Umsetzung in kleinen Codex-Schritten

### Arbeitsregel für Codex

Jeder Schritt wird einzeln umgesetzt.

Codex soll pro Schritt:

1. zuerst vorhandene Dateien lesen,
2. nur den beschriebenen Umfang ändern,
3. keine zukünftigen Module vorweg implementieren,
4. Tests ergänzen,
5. geänderte Dateien auflisten,
6. Ausführungskommandos nennen,
7. offene Annahmen dokumentieren,
8. nach erfolgreicher Prüfung stoppen.

# Phase 0 – Projekt vorbereiten

## Schritt 0.1 – Repository-Grundstruktur

Aufgabe:

- Verzeichnisstruktur anlegen
- `README.md`
- `PLAN.md`
- `.gitignore`
- `.env.example`
- Backend- und Frontend-Verzeichnis
- noch keine Businesslogik

Akzeptanzkriterien:

- Struktur entspricht diesem Plan
- private Verzeichnisse sind ignoriert
- README beschreibt Projektziel knapp
- keine unnötigen Abhängigkeiten

## Schritt 0.2 – Backend initialisieren

Aufgabe:

- FastAPI-Projekt erstellen
- `/health`-Endpoint
- Konfiguration über Pydantic Settings
- pytest einrichten

Akzeptanzkriterien:

- Backend startet lokal
- `/health` liefert HTTP 200
- mindestens ein Test vorhanden
- keine Datenbankintegration

## Schritt 0.3 – Frontend initialisieren

Aufgabe:

- React + TypeScript + Vite
- einfache Startseite
- API-Healthcheck anzeigen

Akzeptanzkriterien:

- Frontend startet
- Backend-Status wird angezeigt
- Fehlerzustand wird verständlich dargestellt

# Phase 1 – Datenbank und Bewerbungsverwaltung

## Schritt 1.1 – PostgreSQL und SQLAlchemy

Aufgabe:

- PostgreSQL über Docker Compose
- SQLAlchemy-Verbindung
- Alembic initialisieren
- Basismodell mit Zeitstempeln

Akzeptanzkriterien:

- Migration kann ausgeführt werden
- Datenbankverbindung wird getestet
- Konfiguration kommt aus `.env`

## Schritt 1.2 – Company-Modell

Aufgabe:

- `Company`-Modell
- Pydantic-Schemas
- Repository
- CRUD-Endpoints
- Tests

Akzeptanzkriterien:

- Unternehmen anlegen, lesen, ändern und löschen
- doppelte Firmennamen sinnvoll behandeln
- API-Tests erfolgreich

## Schritt 1.3 – JobPosting-Modell

Aufgabe:

- `JobPosting`-Modell
- Verknüpfung zu Company
- URL eindeutig speichern
- CRUD-Endpoints
- Tests

Akzeptanzkriterien:

- Stellenanzeige manuell anlegbar
- URL-Duplikate werden verhindert
- Liste filterbar nach Unternehmen und Aktivstatus

## Schritt 1.4 – Application-Modell

Aufgabe:

- `Application`-Modell
- Status-Enum
- Beziehung zu JobPosting
- CRUD-Endpoints
- Tests

Akzeptanzkriterien:

- aus einer Stelle kann ein Bewerbungsprozess angelegt werden
- Status wird validiert
- eine Stelle hat höchstens einen aktiven Bewerbungsvorgang

## Schritt 1.5 – Statushistorie

Aufgabe:

- `ApplicationStatusHistory`
- Service zum kontrollierten Statuswechsel
- bei jedem Statuswechsel Historieneintrag erzeugen
- Tests

Akzeptanzkriterien:

- Status darf nicht direkt ungeprüft überschrieben werden
- Historie zeigt alten und neuen Status
- Zeitstempel ist vorhanden

## Schritt 1.6 – Task-Modell

Aufgabe:

- Tasks mit Priorität, Status und Frist
- Beziehung zu Application
- CRUD-Endpoints
- Filter für offene und fällige Aufgaben
- Tests

Akzeptanzkriterien:

- Aufgaben können Bewerbungen zugeordnet werden
- fällige Aufgaben sind separat abrufbar
- erledigte Aufgaben speichern Abschlusszeitpunkt

# Phase 2 – Erstes Dashboard

## Schritt 2.1 – Bewerbungsübersicht

Aufgabe:

- Frontend-Seite mit Bewerbungsliste
- Filter nach Status
- Unternehmen, Rolle, Datum und nächste Aktion anzeigen

Akzeptanzkriterien:

- Daten kommen aus Backend
- Lade-, Leer- und Fehlerzustände vorhanden
- responsive Darstellung

## Schritt 2.2 – Bewerbungsdetail

Aufgabe:

- Detailansicht
- Status ändern
- Notizen bearbeiten
- Statushistorie anzeigen

Akzeptanzkriterien:

- Statuswechsel wird im Backend protokolliert
- Detailseite aktualisiert sich ohne Neuladen
- Fehler werden angezeigt

## Schritt 2.3 – Aufgabenansicht

Aufgabe:

- offene Aufgaben anzeigen
- nach Frist und Priorität sortieren
- Aufgabe als erledigt markieren

Akzeptanzkriterien:

- überfällige Aufgaben erkennbar
- Filter nach Status
- mobile Nutzung möglich

## Schritt 2.4 – Dashboard-Kennzahlen

Aufgabe:

- Backend-Summary-Endpoint
- Kennzahlen im Frontend

Kennzahlen:

- neue Stellen
- offene Bewerbungen
- fällige Aufgaben
- Bewerbungen ohne Rückmeldung
- Interviews

Akzeptanzkriterien:

- Kennzahlen werden serverseitig berechnet
- Definition jeder Kennzahl dokumentiert
- Tests für Berechnungslogik

# Phase 3 – Manuelle Stellenaufnahme und Analysebasis

## Schritt 3.1 – Stellenanzeige als Text importieren

Aufgabe:

- Formular für Stellen-URL und Text
- Unternehmen auswählen oder neu anlegen
- JobPosting speichern

Akzeptanzkriterien:

- Pflichtfelder validiert
- Text wird unverändert gespeichert
- Duplikate werden erkannt

## Schritt 3.2 – Stellenanzeige als PDF importieren

Aufgabe:

- PDF-Upload
- Text extrahieren
- Originaldatei privat speichern
- JobPosting erzeugen

Akzeptanzkriterien:

- textbasierte PDFs funktionieren
- Fehler bei leerem Text
- Dateipfad nicht öffentlich ausliefern
- OCR noch nicht implementieren

## Schritt 3.3 – Analyse-Schema definieren

Aufgabe:

- Pydantic-Modell `JobAnalysis`
- JSON-Schema für alle Analysefelder
- Beispielobjekt
- Validierungstests

Akzeptanzkriterien:

- Muss- und Kann-Anforderungen getrennt
- Seniorität und Sprache enthalten
- unklare Werte dürfen als `null` markiert werden

## Schritt 3.4 – Regelbasierte Voranalyse

Aufgabe:

- ohne LLM erste Metadaten extrahieren
- Titel
- Unternehmen
- Standort
- häufige Technologien
- E-Mail-Adresse
- Gehaltsangaben

Akzeptanzkriterien:

- deterministische Tests
- keine LLM-Abhängigkeit
- Rohtext bleibt erhalten

# Phase 4 – Bewerbungsbibliothek

## Schritt 4.1 – Markdown-Modullader

Aufgabe:

- Markdown-Dateien laden
- YAML-Frontmatter parsen
- ungültige Dateien melden
- Module als strukturierte Objekte darstellen

Akzeptanzkriterien:

- Sprache, Kategorie und Tags validiert
- fehlerhafte Module werden nicht still ignoriert
- Unit-Tests mit Dummy-Daten

## Schritt 4.2 – Evidence-Modell

Aufgabe:

- Metadaten um Nachweisart ergänzen
- Erfahrungsniveau modellieren

Beispiel:

```yaml
evidence_level: professional
evidence_source: Spirent
verified: true
```

Mögliche Werte:

```text
professional
commercial_project
portfolio_project
training
self_study
planned
```

Akzeptanzkriterien:

- Generator kann professionell und nur gelernt unterscheiden
- ungeprüfte Inhalte werden markiert

## Schritt 4.3 – Bibliotheksübersicht

Aufgabe:

- API zum Auflisten und Filtern der Module
- Frontend-Seite für Modulübersicht
- Inhalt nur lokal anzeigen

Akzeptanzkriterien:

- Filter nach Sprache, Kategorie, Rolle und Tags
- keine Bearbeitung in diesem Schritt

# Phase 5 – AI-Integration

## Schritt 5.1 – LLM-Abstraktion

Aufgabe:

- Provider-Interface
- Ollama-Implementierung
- Mock-Provider für Tests
- Timeout- und Fehlerbehandlung

Akzeptanzkriterien:

- Geschäftslogik kennt Ollama nicht direkt
- Tests laufen ohne echtes Modell
- Modellname konfigurierbar

## Schritt 5.2 – Stellenanalyse mit LLM

Aufgabe:

- Prompt
- strukturierte JSON-Ausgabe
- Pydantic-Validierung
- Wiederholungsversuch bei ungültiger Ausgabe

Akzeptanzkriterien:

- Analyse wird versioniert gespeichert
- Rohantwort optional für Debugging
- keine Überschreibung alter Analysen

## Schritt 5.3 – Embeddings und Index

Aufgabe:

- lokale Embeddings
- Module indexieren
- Metadatenfilter
- Index neu aufbauen können

Akzeptanzkriterien:

- private Bibliothek bleibt lokal
- Sprachfilter funktioniert
- Tests mit kleinem Dummy-Korpus

## Schritt 5.4 – Modul-Retrieval

Aufgabe:

- relevante Module zur Stellenanalyse suchen
- Metadatenfilter vor semantischer Suche
- maximale Trefferzahl begrenzen

Akzeptanzkriterien:

- nur passende Sprache
- keine Company-Module anderer Unternehmen
- Retrieval-Ergebnis nachvollziehbar

## Schritt 5.5 – Match-Analyse

Aufgabe:

- Anforderungen mit Profilmodulen vergleichen
- Bewertung pro Anforderung
- Gesamtbewertung
- Stärken, Lücken und Strategie speichern

Akzeptanzkriterien:

- jede Aussage verweist auf verwendete Module
- fehlende Skills werden nicht als vorhanden dargestellt
- Ergebnis kann manuell verworfen werden

## Schritt 5.6 – Anschreibenentwurf

Aufgabe:

- ausgewählte Module verwenden
- Anschreiben als Markdown erzeugen
- Quellenmodule mitspeichern
- Versionierung

Akzeptanzkriterien:

- maximal eine Seite als Ziel
- keine Fakten außerhalb der Module
- Entwurf ist klar als Entwurf markiert
- keine Versandfunktion

## Schritt 5.7 – Profiltext und Skill-Empfehlung

Aufgabe:

- Profiltext generieren
- Reihenfolge relevanter Skills vorschlagen
- bestehende Skills nicht automatisch verändern

Akzeptanzkriterien:

- 3 bis 5 Sätze
- Zielrolle berücksichtigt
- Vorschlag und aktuelle Version getrennt

# Phase 6 – Job Watcher

## Schritt 6.1 – Source-Adapter-Interface

Aufgabe:

- gemeinsames Interface für Jobquellen
- Ergebnisobjekt für gefundene Stellen
- Mock-Adapter

Akzeptanzkriterien:

- Adapter liefert normalisierte Daten
- Scrapinglogik ist von Datenbanklogik getrennt
- Tests ohne Internet

## Schritt 6.2 – Generischer HTML-Adapter

Aufgabe:

- Suchseite per HTTP laden
- konfigurierbare CSS-Selektoren
- Links normalisieren
- Rate Limit und User-Agent

Akzeptanzkriterien:

- keine Capgemini-Sonderlogik
- Selektoren kommen aus Konfiguration
- Fehler eines Laufs stoppen nicht die Anwendung

## Schritt 6.3 – Capgemini-Adapter

Aufgabe:

- Capgemini-Suchseite analysieren
- vorhandene URL-Parameter beibehalten
- Stellenlinks und Metadaten extrahieren
- nur Berlin bzw. konfigurierte Filter akzeptieren

Akzeptanzkriterien:

- Parser-Fixtures aus gespeicherten HTML-Beispielen
- Tests greifen nicht live auf die Webseite zu
- Änderungen der Seitenstruktur werden als Fehler protokolliert

## Schritt 6.4 – Deduplizierung

Aufgabe:

- `external_id`, URL und Content-Hash auswerten
- neue, geänderte und bekannte Stellen unterscheiden

Akzeptanzkriterien:

- erneuter Lauf erzeugt keine Duplikate
- geänderter Inhalt erzeugt Snapshot
- verschwundene Stelle wird nicht sofort gelöscht

## Schritt 6.5 – Scheduler

Aufgabe:

- aktive Quellen regelmäßig prüfen
- Intervall je Quelle
- Lauf protokollieren

Akzeptanzkriterien:

- manueller Lauf möglich
- parallele doppelte Läufe verhindert
- Fehlerstatus und Laufzeit gespeichert

## Schritt 6.6 – Neue-Stellen-Ansicht

Aufgabe:

- Dashboard-Bereich für neue Stellen
- Stellen prüfen, verwerfen oder als interessant markieren

Akzeptanzkriterien:

- kein automatisches Anlegen einer Bewerbung
- Nutzerentscheidung wird gespeichert
- Quelle und Erfassungszeit sichtbar

# Phase 7 – Workflow-Automatisierung

## Schritt 7.1 – Regelbasierte Task-Vorschläge

Beispiele:

```text
INTERESTING -> Stelle prüfen
PREPARING -> Lebenslauf und Anschreiben vorbereiten
APPLIED -> Nachfassaufgabe nach definierter Frist
INTERVIEW -> Interviewvorbereitung
```

Akzeptanzkriterien:

- Vorschläge sind konfigurierbar
- Duplikate werden verhindert
- Nutzer bestätigt neue Aufgaben

## Schritt 7.2 – Bewerbungs-Workflow

Aufgabe:

- erlaubte Statusübergänge definieren
- ungültige Übergänge verhindern

Beispiel:

```text
DISCOVERED -> REVIEWING
REVIEWING -> INTERESTING
INTERESTING -> PREPARING
PREPARING -> READY_TO_APPLY
READY_TO_APPLY -> APPLIED
```

Akzeptanzkriterien:

- Übergangsregeln getestet
- Sonderfälle wie WITHDRAWN möglich
- Historie bleibt vollständig

## Schritt 7.3 – Erinnerungen

Aufgabe:

- fällige Aufgaben und ausstehende Rückmeldungen erkennen
- In-App-Hinweise erzeugen

Akzeptanzkriterien:

- keine E-Mail-Integration
- Erinnerungen können bestätigt oder verschoben werden
- Regeln dokumentiert

# Phase 8 – Dokumentexport

## Schritt 8.1 – Markdown-Export

Aufgabe:

- Anschreiben und Profiltext exportieren
- Dateinamen standardisieren

Akzeptanzkriterien:

- keine Dateien überschreiben
- Version und Bewerbung referenziert

## Schritt 8.2 – DOCX-Export

Aufgabe:

- bestehende Vorlage verwenden
- Anschreiben in Vorlage einsetzen
- Format beibehalten

Akzeptanzkriterien:

- keine automatische Versendung
- Vorschau bzw. erzeugte Datei verfügbar
- Tests für Platzhalterersetzung

## Schritt 8.3 – PDF-Export

Erst nach stabilem DOCX-Export.

Akzeptanzkriterien:

- PDF entspricht weitgehend DOCX
- Dateierzeugung ist optional
- Fehler werden verständlich angezeigt

# Phase 9 – Qualität und Portfolio

## Schritt 9.1 – Dummy-Datensatz

Aufgabe:

- fiktive Bewerberperson
- fiktive Unternehmen
- fiktive Stellen
- Dummy-Bibliothek

Akzeptanzkriterien:

- keine echten privaten Daten
- kompletter Demo-Workflow möglich

## Schritt 9.2 – Integrationstests

Testfälle:

- Stelle manuell erfassen
- Bewerbung anlegen
- Status ändern
- Task erzeugen
- Stellenanalyse speichern
- Match erzeugen
- Anschreibenentwurf speichern

## Schritt 9.3 – README und Architektur

README enthält:

- Problem
- Lösung
- Funktionsumfang
- Architekturdiagramm
- Datenschutz
- Screenshots
- lokale Installation
- Demo-Daten
- Einschränkungen

## 12. MVP-Abgrenzung

### MVP 1 – Bewerbungsverwaltung

Enthält:

- Unternehmen
- Stellen
- Bewerbungen
- Statushistorie
- Aufgaben
- Dashboard

Noch nicht enthalten:

- Scraping
- RAG
- LLM
- Dokumentgenerierung

### MVP 2 – Bewerbungsassistent

Zusätzlich:

- Stellenanalyse
- Bewerbungsbibliothek
- Matching
- Anschreibenentwurf
- Profiltext

### MVP 3 – Job Monitoring

Zusätzlich:

- Jobquellen
- Capgemini-Adapter
- Scheduler
- neue/geänderte Stellen
- Watchlist-Dashboard

Diese Reihenfolge ist wichtig: Zuerst entsteht ein nützliches Verwaltungssystem. Danach kommen AI und Web-Monitoring hinzu.

## 13. Nicht im ersten Release

Bewusst verschieben:

- Gmail-Versand
- automatische Bewerbung
- Browser-Autofill
- Multi-Agent-System
- komplexe Rollen- und Benutzerverwaltung
- mobile App
- Cloud-Deployment mit echten privaten Daten
- automatische Kontaktrecherche
- allgemeiner Chatbot
- Verarbeitung beliebiger Webseiten ohne Adapter

## 14. Definition of Done pro Codex-Aufgabe

Eine Aufgabe gilt erst als abgeschlossen, wenn:

- Code implementiert ist
- Tests vorhanden und erfolgreich sind
- Linting erfolgreich ist
- Migrationen geprüft sind
- keine Secrets eingecheckt wurden
- README oder technische Dokumentation angepasst wurde
- Codex alle geänderten Dateien nennt
- Codex bekannte Einschränkungen nennt
- der Schritt lokal nachvollziehbar ausführbar ist

## 15. Empfohlener erster Codex-Auftrag

```text
Lies PLAN.md vollständig.

Setze ausschließlich Phase 0, Schritt 0.1 um:
Repository-Grundstruktur.

Anforderungen:
- Lege die im Plan beschriebene Ordnerstruktur an.
- Erstelle README.md mit Projektziel, geplantem Stack und Datenschutz-Hinweis.
- Erstelle .gitignore für Python, Node, IDE-Dateien, .env, private Daten,
  Uploads, generierte Dokumente und lokale Vektordatenbanken.
- Erstelle .env.example ohne echte Zugangsdaten.
- Implementiere noch keine Businesslogik und installiere noch keine Abhängigkeiten.
- Ändere PLAN.md nicht.

Liefere danach:
1. Liste aller erstellten Dateien
2. kurze Begründung der Struktur
3. Hinweise zu offenen Annahmen
4. empfohlene Prüfkommandos

Stoppe danach und warte auf den nächsten Auftrag.
```

## 16. Portfolio-Kurzbeschreibung

> AI Application Assistant is a privacy-focused workflow application for managing job opportunities, application statuses, tasks and deadlines. It monitors configured career pages, analyzes job descriptions, matches requirements against a verified local profile library and creates reviewable application drafts using local language models. All critical actions remain under human control, and the public repository contains only anonymized demo data.
