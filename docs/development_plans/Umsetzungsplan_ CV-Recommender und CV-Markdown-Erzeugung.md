# Umsetzungsplan: CV-Recommender und CV-Markdown-Erzeugung

## Ziel

Aus einer konkreten Stellenanzeige und dem passenden Master-Profil soll der Assistent einen stellenbezogenen Lebenslauf als Markdown erzeugen.

Eingaben:

```text
Stelle
+
strukturierte Stellenanalyse / Matching
+
Master-Profil DE oder EN
        ↓
CV Recommendation
        ↓
CV.md
```

Der erzeugte CV soll anschließend manuell geprüft und bearbeitet werden können.

Noch nicht Bestandteil:

- Anschreiben
- PDF-Erzeugung
- HTML/CSS/WeasyPrint
- automatischer Versand
- automatisches Überschreiben bestehender Profildaten

---

## 1. Sprachauswahl

Für die CV-Generierung muss festgelegt werden:

```text
de
en
```

Standard:

- deutsche Stellenanzeige → deutsches Master-Profil
- englische Stellenanzeige → englisches Master-Profil

Falls Sprache nicht eindeutig erkannt werden kann, Benutzer auswählen lassen.

Keine automatische Übersetzung des jeweils anderen Master-Profils.

---

## 2. Datenbasis

Der Recommender erhält:

### Stelle

Vorhandene strukturierte Daten verwenden, insbesondere:

```text
Jobtitel
Unternehmen
Anforderungen
Aufgaben
Skills
Seniorität
Matching-Ergebnisse
Skill-Evidenz
weitere bereits extrahierte relevante Informationen
```

### Kandidat

Aktuelle Version von:

```text
master_profile_de.md
```

oder:

```text
master_profile_en.md
```

Das Master-Profil ist die verbindliche Wissensbasis für Aussagen über den Kandidaten.

Keine Fähigkeiten, Erfahrungen, Projekte oder Erfolge erfinden.

---

## 3. Aufgabe des CV-Recommenders

Der Recommender soll nicht einfach das Master-Profil kopieren.

Er soll anhand der Stelle auswählen und priorisieren:

```text
profile_job_title
profile_text
skills
working_experience
education
certificates
selected_projects
references
```

Dabei:

- relevante Inhalte priorisieren
- irrelevante Inhalte weglassen
- vorhandene Formulierungen stellenbezogen optimieren
- keine Fakten verändern
- keine neuen Erfahrungen oder Fähigkeiten hinzufügen
- messbare Erfolge aus dem Master-Profil erhalten

---

## 4. Empfohlene zweistufige Verarbeitung

Nicht sofort einen fertigen CV erzeugen.

Zuerst strukturierte Empfehlung erstellen:

```text
CVRecommendation

recommended_job_title
profile_summary

selected_skill_categories
selected_skills

experience_entries
    selected_bullets

selected_education

selected_certificates

selected_projects

selected_references
```

Zusätzlich pro Auswahl optional:

```text
reason
source_reference
```

Dadurch bleibt nachvollziehbar, warum etwas ausgewählt wurde.

---

## 5. Validierung der Empfehlung

Vor der Markdown-Erzeugung prüfen:

- alle ausgewählten Skills kommen im Master-Profil vor
- alle Experience-Bullets stammen aus dem Master-Profil oder sind nur sprachlich umformuliert
- Projekte existieren im Master-Profil
- keine Arbeitgeber, Abschlüsse oder Zeiträume wurden verändert
- keine neuen Zahlen oder Erfolge wurden erfunden

Wenn eine Aussage nicht auf das Master-Profil zurückgeführt werden kann:

```text
validation_warning
```

und nicht stillschweigend übernehmen.

---

## 6. Benutzeransicht „CV-Empfehlung“

Auf der Job-/Bewerbungsdetailseite neue Aktion:

```text
CV erstellen
```

Danach zunächst Review-Ansicht:

```text
CV-Empfehlung
────────────────────────

Zielrolle
Data Scientist

Profil
[...]

Skills
✓ Python
✓ Forecasting
✓ Feature Engineering
✓ PostgreSQL
...

Berufserfahrung
Spirent Technologies
✓ Bullet 1
✓ Bullet 2
...

Projekte
✓ Electricity Price Forecasting
✓ AI Job Application Assistant

[CV erzeugen]
```

Der Benutzer soll Empfehlungen vor der endgültigen Erzeugung abwählen können.

Noch kein komplexer Drag-and-Drop-Editor notwendig.

---

## 7. CV-Markdown erzeugen

Nach Bestätigung wird ein vollständiges Markdown-Dokument erzeugt.

Beispielstruktur:

```markdown
# Yuchuan Liu

## Data Scientist

Kontaktinformationen ...

## Profile

...

## Skills

### Machine Learning
- Forecasting
- Feature Engineering
- Model Evaluation

### Data Engineering
- ETL Pipelines
- PostgreSQL

## Professional Experience

### Senior Support Engineer
Spirent Technologies GmbH | 2010-06 – 2023-09

- ...
- ...

## Selected Projects

### Electricity Price Forecasting
...

## Education
...

## Certifications
...
```

Die sichtbaren Überschriften sollen in der jeweiligen CV-Sprache ausgegeben werden.

Die internen Master-Profil-Keys bleiben weiterhin englisch.

---

## 8. CV-Dokument speichern

Neue Tabelle oder bestehendes Dokumentmodell erweitern.

Beispiel:

```text
application_documents

id
application_id
document_type
language
content
version
is_current
created_at
updated_at
```

`document_type`:

```text
cv
```

Später:

```text
cover_letter
```

Markdown als PostgreSQL `TEXT`.

---

## 9. Versionierung

Bei erneuter CV-Erzeugung:

```text
CV v1
CV v2
CV v3
```

Neue Version:

- bisherige Version bleibt erhalten
- neue Version wird `is_current = true`
- bisher aktuelle Version wird `false`

Auch manuell bearbeitete Fassungen werden als Version gespeichert.

---

## 10. Markdown bearbeiten

Für die aktuelle Version einen einfachen Markdown-Editor bereitstellen:

```text
[Bearbeiten]
[Speichern]
```

Beim Speichern:

- neue Version erzeugen
- vorhandene Version nicht überschreiben

Optional:

```text
[Vorschau]
```

Gerendertes Markdown reicht zunächst.

Noch keine PDF-Vorschau.

---

## 11. LLM-Prompting

Prompt klar in zwei Bereiche trennen:

```text
JOB CONTEXT
...

MASTER PROFILE
...
```

Zentrale Regeln:

```text
Use only facts contained in the master profile.
Do not invent skills, experience, achievements or qualifications.
Tailor wording and selection to the job posting.
Prefer evidence-backed achievements over generic statements.
Return structured output matching the defined schema.
```

Structured Output / JSON-Schema verwenden, sofern die bestehende LLM-Integration dies unterstützt.

Markdown erst aus dem validierten strukturierten Ergebnis erzeugen.

---

## 12. Bestehendes Matching nutzen

Keine zweite vollständige Jobanalyse im CV-Recommender implementieren.

Vorhandene Daten verwenden:

```text
Job Extraction
       ↓
Matching
       ↓
CV Recommendation
```

Der CV-Recommender soll auf bereits vorhandener Analyse aufbauen.

Nur wenn notwendige Informationen fehlen, kann die Stellenbeschreibung zusätzlich als Kontext mitgegeben werden.

---

## 13. UI-Abgrenzung

Noch kein umfassendes Redesign.

Minimal ergänzen:

Auf Job-/Bewerbungsdetail:

```text
CV
─────────────────
Noch kein CV vorhanden

[CV empfehlen]
```

Nach Generierung:

```text
CV
─────────────────
Version 2 · aktuell

[Anzeigen]
[Bearbeiten]
[Neue Empfehlung]
[Versionen]
```

---

## 14. Bestehender PDF-CV-Import

Unverändert lassen.

Nicht in den neuen Workflow integrieren.

Der neue Standardworkflow lautet:

```text
Master-Profil
→ CV Recommendation
→ CV Markdown
```

PDF-Import bleibt Legacy-/Zusatzfunktion.

---

## Nicht Bestandteil dieses Schritts

Noch nicht implementieren:

- Anschreiben
- PDF
- HTML-Templates
- CSS
- WeasyPrint
- mehrere visuelle CV-Layouts
- automatische Übersetzung
- automatisches Absenden
- vollständiges Verwaltungs-UI-Redesign

---

## Akzeptanzkriterien

Die Umsetzung ist abgeschlossen, wenn:

1. Für eine Stelle kann eine CV-Empfehlung erzeugt werden.
2. Automatisch wird das passende DE-/EN-Master-Profil verwendet.
3. Die Empfehlung basiert ausschließlich auf vorhandenen Kandidatenfakten.
4. Skills, Erfahrungen und Projekte werden stellenbezogen ausgewählt.
5. Der Benutzer kann die Auswahl vor der Generierung prüfen.
6. Daraus wird ein vollständiger CV als Markdown erzeugt.
7. Der CV wird in PostgreSQL gespeichert.
8. Neue Generierungen/Bearbeitungen erzeugen Versionen.
9. Alte Versionen bleiben abrufbar.
10. Der aktuelle CV kann als Markdown angezeigt und bearbeitet werden.
11. Bestehende Profil- und Master-Profil-Daten werden nicht verändert.
12. PDF- und Anschreiben-Funktionen bleiben zunächst unangetastet.