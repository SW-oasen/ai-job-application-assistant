# Umsetzungsplan: Master-Profile DE/EN importieren und versionieren

## Ziel

Die Anwendung soll zwei sprachabhängige Master-Profile als Markdown verwalten:

- Deutsch
- Englisch

Die Master-Profile dienen später als Grundlage für CV- und Anschreiben-Generierung.

In diesem Schritt werden nur Import, Speicherung, Versionierung und Anzeige umgesetzt.

Nicht Bestandteil dieses Schritts:

- CV-Generierung
- Anschreiben-Generierung
- PDF-Erzeugung
- automatische Synchronisation mit bestehenden Profil-, Skill-, Erfahrungs- oder Projektdaten
- UI-Redesign der gesamten Verwaltungsseite

## Grundprinzip

Die Master-Profile werden bewusst zusätzlich zu den bereits vorhandenen strukturierten Profildaten gespeichert.

Sie sind:

- kuratierte LLM-Arbeitsgrundlage
- sprachabhängig
- Markdown-basiert
- versioniert

Bestehende strukturierte Daten bleiben unverändert.

## Datenmodell

Neue Tabelle, z. B. `master_profiles`.

Empfohlene Felder:

```text
id
profile_id
language
content
version
is_current
original_filename
created_at
updated_at
```

Optional:

```text
content_hash
file_size
```

### Werte für `language`

```text
de
en
```

### Speicherung

Markdown-Inhalt als PostgreSQL-`TEXT` speichern.

Keine BLOB-Speicherung notwendig, da Markdown direkt textuell verarbeitet werden soll.

## Constraints

Pro Profil und Sprache darf nur eine aktuelle Version existieren.

Beispiel:

```text
profile_id = 123
language = de
version = 1
is_current = false

profile_id = 123
language = de
version = 2
is_current = true
```

Geeignete Unique-/Partial-Constraint verwenden, sodass `(profile_id, language)` nur einmal `is_current = true` besitzen kann.

## Versionierung

Beim Import einer neuen Datei für eine bereits vorhandene Sprache:

1. aktuelle Version ermitteln
2. bestehende aktuelle Version auf `is_current = false` setzen
3. Versionsnummer erhöhen
4. neuen Markdown-Inhalt speichern
5. neue Version auf `is_current = true` setzen

Die alte Version bleibt erhalten.

Der Vorgang soll innerhalb einer DB-Transaktion erfolgen.

## Backend-Service

Neue Service-Schicht, z. B.:

```text
MasterProfileService
```

Funktionen:

```text
import_master_profile(...)
get_current_master_profile(...)
list_master_profile_versions(...)
get_master_profile_version(...)
set_current_version(...)
delete_version(...)
```

Optional zunächst weglassen:

```text
delete_version(...)
set_current_version(...)
```

Falls die erste Umsetzung möglichst klein bleiben soll, reichen:

```text
import
get_current
list_versions
```

## Markdown-Validierung

Beim Import nur eine leichte Validierung durchführen.

Prüfen:

- Datei ist `.md`
- Inhalt ist nicht leer
- UTF-8 lesbar
- erwartete Grundstruktur vorhanden

Mindestens erwartete Schlüssel:

```text
# profile_name
## profile_job_title
## profile_text
## skills
## working_experience
## education
## certificates
## references
## selected_projects
```

Bei fehlenden Pflichtbereichen:

- Import nicht stillschweigend durchführen
- verständliche Validierungsfehler anzeigen

Keine komplexe semantische Validierung in diesem Schritt.

## Sprache

Sprache beim Upload explizit auswählen:

```text
Deutsch
English
```

Nicht allein aus dem Inhalt automatisch erkennen.

Optional kann der Dateiname als Hinweis verwendet werden, z. B.:

```text
master_profile_de.md
master_profile_en.md
```

Die explizite Auswahl bleibt aber maßgeblich.

## API

Beispielhafte Endpoints:

```text
POST /profiles/{profile_id}/master-profiles
GET  /profiles/{profile_id}/master-profiles
GET  /profiles/{profile_id}/master-profiles/{language}
GET  /profiles/{profile_id}/master-profiles/{language}/versions
```

Upload-Request enthält:

```text
language
file
```

Alternativ kann der Markdown-Inhalt direkt als Request-Body übertragen werden, falls dies besser zur bestehenden Architektur passt.

## Web-GUI

Auf der aktuellen Profilbearbeitungsseite einen zusätzlichen Menüpunkt hinzufügen:

```text
Master-Profile
```

Noch kein großes Layout-Redesign.

Der Menüpunkt soll sich in die bestehende linke Navigation einfügen.

## Master-Profile-Ansicht

Kompakte Darstellung:

```text
Master-Profile

Deutsch
Status: vorhanden
Aktuelle Version: 3
Datei: master_profile_de.md
[Neue Version importieren]
[Anzeigen]
[Versionen]

Englisch
Status: vorhanden
Aktuelle Version: 2
Datei: master_profile_en.md
[Neue Version importieren]
[Anzeigen]
[Versionen]
```

Falls noch nicht vorhanden:

```text
Deutsch
Status: nicht vorhanden
[Master-Profil importieren]
```

## Import-Dialog

Felder:

```text
Sprache
Datei auswählen
```

Danach:

```text
[Importieren]
```

Vor dem Speichern:

- Dateityp prüfen
- Markdown validieren
- erkannte Fehler anzeigen

Optional eine einfache Textvorschau vor dem Import.

## Anzeige

Das aktuelle Master-Profil zunächst einfach lesbar anzeigen.

Möglichkeiten:

- gerendertes Markdown
- zusätzlich optional Raw-Markdown

Keine vollständige Markdown-Editor-Funktion in diesem Schritt notwendig.

## Versionshistorie

Pro Sprache:

```text
Version 3   aktuell   2026-08-23
Version 2             2026-08-21
Version 1             2026-08-18
```

Zunächst reicht read-only.

Rollback oder „Version wieder aktiv setzen“ kann später ergänzt werden.

## Bestehende Daten

Wichtig:

Die bestehenden Bereiche bleiben unverändert:

```text
Profil
Skills
Skill-Evidenz
Berufserfahrung
Portfolio-Projekte
Ausbildung
Zertifikate
Referenzen
Import-Vorschläge
```

Der Master-Profil-Import soll keine dieser Daten automatisch verändern.

Keine Synchronisation und kein Merge in diesem Schritt.

## Bestehender CV-PDF-Import

Bestehende Funktion nicht löschen.

Aber:

- keine Erweiterung in diesem Schritt
- nicht mit Master-Profil-Import koppeln
- vorerst Legacy-/Zusatzfunktion bleiben lassen

## Technische Abgrenzung

Nicht implementieren:

- CV-Recommender
- Anschreiben-Recommender
- Markdown-zu-PDF
- WeasyPrint
- Templates
- automatische Übersetzung DE ↔ EN
- automatischer Vergleich zwischen strukturierten Profildaten und Master-Profil
- automatische Synchronisation
- gesamtes UI-Redesign

## Akzeptanzkriterien

Die Umsetzung ist fertig, wenn:

1. Für ein Profil kann ein deutsches Master-Profil importiert werden.
2. Für dasselbe Profil kann ein englisches Master-Profil importiert werden.
3. Markdown wird in PostgreSQL gespeichert.
4. Ein erneuter Import erzeugt eine neue Version.
5. Genau eine Version je Sprache ist aktuell.
6. Alte Versionen bleiben abrufbar.
7. Die aktuelle Version kann in der Web-GUI angezeigt werden.
8. Der Status DE/EN ist auf der Profilseite sichtbar.
9. Bestehende Profildaten werden durch den Import nicht verändert.
10. Bestehender CV-PDF-Import funktioniert unverändert weiter.