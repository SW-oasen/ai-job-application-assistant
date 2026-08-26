# 04 – UI-Redesign: Job-Detail

## Ziel

Die sehr umfangreiche Seite `/jobs/{job_id}` neu strukturieren, ohne
fachliche Funktionen zu verändern. Sie bleibt der zentrale
Arbeitsbereich für eine konkrete Stelle und Bewerbung.

## Risiko und Vorbereitung

`job-detail.html` enthält umfangreiche UI- und JavaScript-Logik. Keine
Einmal-Neuschreibung. Vorher sichtbare Bereiche, Buttons, API-Aufrufe,
DOM-IDs/Data-Attribute, Lazy Loading, Editierzustände, Matching/Reviews,
Bewerbung und CV-Recommender vollständig inventarisieren.

## Zielstruktur

Empfohlene obere Ebene:

`[ Übersicht ] [ Analyse & Matching ] [ Bewerbung ] [ CV ]`

Später kann Anschreiben ergänzt werden.

### Übersicht

Jobtitel, Unternehmen, Status, Quelle/Bewerbungsweg, wichtige Metadaten,
Qualifikations-Fit, Ziel-Fit und zentrale Aktionen in kompakten
Summary-Karten.

### Analyse & Matching

Extrahierte Anforderungen/Tätigkeiten/Rahmenbedingungen, Evidenz,
Senioritätsabgleich, Qualifikations-Fit, Ziel-Fit und
Review-/Qualitätshinweise. Side-by-Side-Vergleiche bevorzugen, z. B.
Anforderung links und Evidenz rechts.

### Originalanzeige

Bleibt Referenz für Extraktionsqualität. Standardmäßig eingeklappt,
weiterhin lazy geladen, nicht initial im DOM, nach erstem Laden
clientseitig gecacht. Keine aggressive Bereinigung des Originals.

### Bewerbung

Bewerbungsstatus, Ereignisverlauf, Ereignisse hinzufügen/löschen,
archivierte Unterlagen, Bewerbungsweg/Quelle und bestehende
Bewerbungsaktionen. Timeline und Eingabe möglichst
kompakt/nebeneinander.

### CV

CV-Empfehlung bleibt jobbezogen. Master-Profil/Sprache/Version,
Empfehlung, Profiltext, Skills, Experience/Bullets, Projekte,
Ausbildung/Zertifikate, optionale Referenzen, CV-Markdown und Versionen
erhalten. Auswahlbereiche mit Desktopbreite kompakt gruppieren.

## Migrationsstrategie

1.  Funktions-/API-Inventur.
2.  Neue Bereichsnavigation ergänzen, alte Inhalte noch erhalten.
3.  Übersicht migrieren und testen.
4.  Analyse & Matching migrieren und testen.
5.  Originalanzeige/Lazy Loading testen.
6.  Bewerbung migrieren und testen.
7.  CV zuletzt migrieren und testen.
8.  Erst danach alte Layoutstrukturen entfernen.
9.  Keine Matching-/CV-Fachlogik gleichzeitig refactoren.

## Umsetzungsstand

Abgeschlossen:

- kompaktes Übersichtsfeld oberhalb des Arbeitsbereichs;
- unabhängige Desktop-Spalten ohne statische Lücken;
- einheitliche Karten- und Button-Optik für Metadaten, Matching,
  Bewerbungsverlauf, Dokumente und CV;
- Bewerbungsereignisse als anklickbare Liste mit Inline-Editor und Schutz vor
  dem Verwerfen ungespeicherter Änderungen;
- Ziel-Fit und Qualifikations-Fit als direkte Umschalt-Buttons;
- Metadaten-Editor mit derselben Abfrage beim Schließen mit ungespeicherten
  Änderungen;
- Originalanzeige weiterhin lazy geladen und erst beim Öffnen abgerufen.

Die Oberfläche ist bewusst desktopoptimiert. Responsive Verhalten ist kein
Bestandteil dieses Redesigns.

## Regressionstests

Job laden; Metadaten bearbeiten; Original initial ungeladen und beim
Öffnen korrekt laden; Extraktion; Matching/Evidenzen/Fits; Reviews;
Bewerbungsstatus; Ereignis hinzufügen/löschen und Statusneuberechnung;
Dokumente; CV-Empfehlung DE/EN; Auswahl ändern; Markdown erzeugen;
Versionierung; Fehlerzustände; Archivworkflow.

## Nicht Bestandteil

Matching-Algorithmus, Extraktionsoptimierung, CV-Prompting, Anschreiben,
PDF, Dashboard oder Mobile/Responsive.

## Akzeptanzkriterien

Alle Funktionen bleiben erhalten; wenige klare Arbeitsbereiche;
Originalanzeige bleibt lazy-loaded; CV bleibt im Job-Kontext;
Desktopbreite reduziert Seitenlänge deutlich; keine Regression bei
Matching, Bewerbung oder CV.
