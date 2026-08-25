# Umsetzungsplan: CV-Recommender vollständig abschließen

## Ziel

Den bestehenden CV-Recommender zu einem vollständigen Workflow ausbauen:

```text
Stellenanzeige
+ Matching / Extraktion
+ Master-Profil DE/EN
        ↓
CV Recommendation
        ↓
Review / Anpassung
        ↓
finales CV-Markdown
        ↓
Versionierung
```

Nach diesem Schritt soll die fachliche CV-Generierung abgeschlossen sein.

Noch nicht Bestandteil:

- PDF-Rendering
- HTML/CSS-Templates
- WeasyPrint
- Anschreiben

## 1. Recommendation vervollständigen

Die bestehende Recommendation soll alle für den CV benötigten Entscheidungen enthalten:

```text
recommended_job_title
recommended_profile_text

selected_skill_categories
selected_skills

selected_experience_entries
selected_experience_bullets

selected_projects

selected_education
selected_certificates

selected_references
```

Nicht relevante Inhalte des Master-Profils werden bewusst nicht übernommen.

## 2. Stellenbezogene Priorisierung

Der Recommender soll Inhalte anhand der Stellenanforderungen priorisieren.

Priorität:

1. Muss-/Kernanforderungen der Stelle
2. direkt belegbare praktische Erfahrung
3. relevante Projekte
4. relevante Tools und Technologien
5. ergänzende Kompetenzen
6. allgemeine oder nur schwach relevante Inhalte

Keine reine Keyword-Übernahme.

## 3. Evidenzprinzip

Jede Empfehlung muss auf Kandidateninformationen zurückführbar sein.

Keine Erfindung von:

- Skills
- Technologien
- Berufserfahrung
- Verantwortlichkeiten
- Erfolgszahlen
- Ausbildung
- Zertifikaten
- Projekten

Sprachliche Umformulierungen sind erlaubt.

Fakten dürfen dadurch nicht verstärkt oder verändert werden.

## 4. Recommendation-Review in der GUI

Vor Erstellung des CV-Markdowns soll die bestehende Recommendation editierbar sein.

Mindestens:

```text
Zieljobtitel
Profiltext

Skills
[x] Python
[x] Forecasting
[ ] Power BI
...

Berufserfahrung
[x] Bullet 1
[x] Bullet 2
[ ] Bullet 3

Projekte
[x] Electricity Price Forecasting
[x] AI Job Application Assistant
[ ] Store Finder
```

Benutzer soll Inhalte:

- aktivieren/deaktivieren
- optional umsortieren
- Profiltext bearbeiten
- Zieljobtitel bearbeiten

können.

Kein komplexes Drag-and-Drop notwendig, falls einfache Reihenfolge-Steuerung ausreicht.

## 5. CV-Markdown-Template

Eine feste semantische CV-Struktur definieren.

Beispiel:

```markdown
# {{ profile_name }}

## {{ recommended_job_title }}

{{ contact_information }}

## Profil

{{ profile_text }}

## Kompetenzen

### Machine Learning
- ...
- ...

### Data Engineering
- ...
- ...

## Berufserfahrung

### Senior Support Engineer
**Spirent Technologies GmbH | 2010-06 – 2023-09**

- ...
- ...

## Ausgewählte Projekte

### Electricity Price Forecasting

...

## Ausbildung

...

## Zertifikate

...

## Sprachen

...

## Referenzen

...
```

Englische Version mit entsprechenden sichtbaren Überschriften.

Interne Keys bleiben weiterhin englisch.

## 6. Template und Inhalt trennen

CV-Markdown nicht vollständig frei vom LLM erzeugen lassen.

Empfohlener Ablauf:

```text
LLM
↓
strukturierte CV Recommendation
↓
Validierung
↓
deterministischer Markdown Renderer
↓
CV.md
```

Dadurch bleiben:

- Reihenfolge
- Überschriften
- Formatierung
- Markdown-Struktur

deterministisch.

Das LLM ist hauptsächlich für Auswahl und Formulierung verantwortlich.

## 7. Profiltext

Der Profiltext darf stellenbezogen neu formuliert werden.

Regeln:

- ca. 3–5 Sätze
- relevant zur Zielrolle
- keine generischen Floskeln
- vorhandene Erfahrung verdichten
- keine neuen Fakten
- keine überhöhte Seniorität
- zentrale technische und fachliche Stärken der Stelle aufgreifen

Der Master-Profiltext dient als Grundlage, muss aber nicht wortgleich übernommen werden.

## 8. Skills

Skills nicht einfach vollständig übernehmen.

Der Recommender soll:

- relevante Kategorien auswählen
- relevante Skills auswählen
- redundante Skills vermeiden
- Reihenfolge nach Stellenrelevanz bestimmen

Beispiel:

```text
Machine Learning
Python · Forecasting · Time Series · XGBoost · MLflow

Data Engineering
ETL Pipelines · PostgreSQL · API Integration

AI Engineering
RAG · LLM Applications · Workflow Automation
```

Keine Skills aufnehmen, die nur in der Stellenanzeige stehen, aber nicht im Master-Profil.

## 9. Berufserfahrung

Alle relevanten Stationen grundsätzlich erhalten, aber Bulletpoints stellenbezogen auswählen.

Beispiel:

```text
Spirent
4 verfügbare Master-Bullets
↓
2–3 für konkrete Stelle auswählen
```

Wichtige belegbare Erfolge und Zahlen bevorzugen.

Berufsbezeichnung, Unternehmen und Zeitraum nicht verändern.

## 10. Projekte

Pro Stelle eine kleine Auswahl treffen.

Standardziel:

```text
2–3 relevante Projekte
```

Nicht nach Aktualität, sondern nach Stellenrelevanz priorisieren.

Projektbeschreibung darf gekürzt und stellenbezogen formuliert werden.

Technologien nur übernehmen, wenn sie im jeweiligen Master-Projekt enthalten sind.

## 11. Ausbildung und Zertifikate

Nicht aggressiv kürzen.

Für normalen CV:

- Hochschulabschlüsse behalten
- relevante Weiterbildung behalten
- relevante Zertifikate auswählen

Bei Platzproblemen zuerst weniger relevante Zertifikate reduzieren, nicht Kernqualifikationen.

## 12. Referenzen

Referenzen optional machen.

Recommendation soll entscheiden können:

```text
include_references = true / false
```

Standard darf zunächst auf bestehender CV-Konvention beruhen.

Keine Referenz verändern oder neu erzeugen.

## 13. CV-Dokumentmodell

Bestehendes Dokumentmodell verwenden bzw. vervollständigen:

```text
application_id
document_type = cv
language
content
version
is_current
created_at
updated_at
```

Optional zusätzlich speichern:

```text
source_master_profile_version
source_recommendation_id
generation_metadata
```

Damit später nachvollziehbar bleibt, auf welcher Masterprofil-Version ein CV basiert.

## 14. Versionierungslogik

Folgende Aktionen erzeugen neue Versionen:

- CV neu generieren
- Recommendation erneut anwenden
- Benutzer speichert manuell bearbeitetes Markdown

Vorhandene Version niemals überschreiben.

Beispiel:

```text
CV v1 – initial generated
CV v2 – manually edited
CV v3 – regenerated
```

Nur eine aktuelle Version.

## 15. Markdown-Editor

CV nach Erzeugung direkt bearbeitbar machen.

Funktionen:

```text
Anzeigen
Bearbeiten
Speichern als neue Version
Versionen anzeigen
```

Optional bereits:

```text
Markdown-Vorschau
```

Noch keine PDF-Vorschau.

## 16. Regeneration

Aktion:

```text
Neue CV-Empfehlung erzeugen
```

Dabei bestehende CV-Versionen nicht verändern.

Workflow:

```text
bestehende Bewerbung
↓
neue Recommendation
↓
Review
↓
neue CV-Version
```

## 17. Validierung vor Speicherung

Vor Erstellung des finalen CV:

- ausgewählte Experience existiert
- ausgewählte Projekte existieren
- Skills existieren
- Zeiträume unverändert
- Unternehmen unverändert
- Zahlen/Erfolge durch Masterprofil gedeckt
- Sprache entspricht ausgewähltem Masterprofil

Bei Abweichungen Generierung abbrechen oder Warnung anzeigen.

## 18. Fehlende Masterdaten

Wenn die Stelle etwas verlangt, das im Masterprofil nicht belegt ist:

Nicht ergänzen.

Optional Recommendation-Hinweis:

```text
Nicht belegbare Stellenanforderungen:
- Azure
- Kubernetes
```

Diese Information gehört aber nicht automatisch in den CV.

## 19. UI auf Job-/Bewerbungsdetail

Kompakter Bereich:

```text
Lebenslauf
────────────────────────

Master-Profil: DE v3

CV-Empfehlung
✓ vorhanden

Aktueller CV
Version 4

[Empfehlung bearbeiten]
[CV anzeigen]
[CV bearbeiten]
[Neue Empfehlung]
[Versionen]
```

Keine größere Layout-Änderung in diesem Schritt.

## 20. Bestehende strukturierte Profildaten

Weiterhin nicht mit Masterprofil synchronisieren.

Der CV-Workflow verwendet als Kandidaten-Source primär:

```text
Master-Profil
```

Vorhandene strukturierte Profilinformationen können ergänzend für bereits bestehende Funktionen genutzt werden.

Keine neue Synchronisationslogik implementieren.

## 21. Legacy-CV-PDF-Import

Unverändert bestehen lassen.

Nicht mehr als Standardweg verwenden.

Standard:

```text
Master-Profil
→ Recommendation
→ Markdown-CV
```

## 22. Tests

Mindestens testen:

- deutsche Stelle + DE-Masterprofil
- englische Stelle + EN-Masterprofil
- stark passender Job
- teilweise passender Job
- Job verlangt unbekannte Skills
- Recommendation erneut erzeugen
- manuelle CV-Bearbeitung
- Versionswechsel
- fehlendes Masterprofil
- ungültige Recommendation
- kein relevantes Projekt vorhanden

Besonders prüfen:

- keine Halluzinationen
- keine veränderten Zahlen
- keine Übernahme von Jobanforderungen als angebliche Kandidatenskills

## Akzeptanzkriterien

Der CV-Recommender ist fachlich abgeschlossen, wenn:

1. Recommendation aus Job + Masterprofil erzeugt wird.
2. Benutzer Recommendation prüfen und verändern kann.
3. Skills stellenbezogen ausgewählt werden.
4. Experience-Bullets stellenbezogen ausgewählt werden.
5. Projekte stellenbezogen ausgewählt werden.
6. Profiltext stellenbezogen erzeugt wird.
7. Keine unbelegten Fakten in den CV gelangen.
8. Finales CV-Markdown deterministisch erzeugt wird.
9. DE und EN funktionieren.
10. CV manuell editierbar ist.
11. Änderungen neue Versionen erzeugen.
12. Alte Versionen erhalten bleiben.
13. Quelle und Masterprofil-Version nachvollziehbar bleiben.
14. Bestehender PDF-Import unverändert bleibt.

## Danach

Nach Abschluss dieses Schritts gilt die inhaltliche CV-Generierung als fertig.

Nächste getrennte Schritte:

```text
1. Anschreiben-Generierung auf Basis von Job + Masterprofil + CV
2. Markdown → HTML/CSS → PDF
3. gemeinsames Template-/Layout-System
4. später UI-Redesign der Verwaltung
```