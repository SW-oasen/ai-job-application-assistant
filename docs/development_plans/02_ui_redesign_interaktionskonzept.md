# 02 – UI-Redesign: Interaktionskonzept

## Voraussetzung

`01_ui_redesign_informationsarchitektur.md` ist verbindliche Grundlage.

## Ziel

Gemeinsame Desktop-UI-Regeln definieren, bevor einzelne Seiten umgebaut
werden.

## Desktop-Grundlayout

- Gesamte Browserbreite mit kleinen äußeren Rändern nutzen.
- Keine zentrale schmale `max-width`.
- Breite Inhalte in 2–3 Spalten organisieren, wenn fachlich sinnvoll.
- Große Textbereiche dürfen volle Breite nutzen.
- Kein Responsive-/Mobile-Scope.

## Navigation und Hierarchie

Globale Hauptziele: Jobs & Bewerbungen, Verwaltung, später optional
Dashboard. Job-Detail wird aus einer konkreten Stelle geöffnet.

UI-Hierarchie: Seite → Arbeitsbereich/Tab → Karte/Panel →
Detail/Accordion/Dialog.

## Karten

Karten sind fachliche Gruppen, keine Dekoration. Sie zeigen
Schlüsselinformationen und häufige Aktionen direkt; seltene Details
können eingeklappt werden. Unabhängige Karten dürfen nebeneinander
stehen.

## Tabs

Tabs für größere Arbeitsbereiche derselben Seite verwenden. Tab-Wechsel
darf ungespeicherte Eingaben nicht stillschweigend verlieren.

## Accordions und Lazy Loading

Geeignet für Original-Stellenanzeige, technische Details, lange
Evidenz-/Review-Informationen und Versionshistorien. Bestehendes Lazy
Loading großer Inhalte erhalten.

## Formulare

- Kurze Felder nebeneinander.
- Zusammengehörige Felder gruppieren.
- Breite Textareas nur für lange Inhalte.
- Speichern und destructive Aktionen klar trennen.
- Desktopfläche nutzen statt jedes Feld auf eine eigene Zeile zu setzen.

## Listen und Tabellen

Kompakte Tabellen für gleichartige Datensätze; Karten für heterogene
Einträge. Statusinformationen möglichst in derselben Zeile.

## Aktionen

Pro Bereich Primary, Secondary, Destructive und Detail unterscheiden.
Nicht mehrere gleichgewichtete Primäraktionen nebeneinander.

## Status und Feedback

Bestehende Success-/Warning-/Error-Rückmeldungen erhalten und möglichst
lokal beim betroffenen Bereich anzeigen. Ladezustände sichtbar machen.

## Funktionalität schützen

- API-Endpunkte nicht aus Designgründen ändern.
- Event-Logik nicht gleichzeitig neu schreiben, wenn nur Layout geändert
  wird.
- IDs/Data-Attribute bewusst migrieren.
- Lazy Loading, Bestätigungsdialoge, Versionierung und
  Validierungsfehler erhalten.

## Visuelle Richtung

Ruhig, kompakt, funktional, moderne Desktop-Verwaltungsoberfläche, klare
Hierarchie, weniger vertikaler Leerraum. Vorhandene Farbwelt kann
zunächst bleiben.

## Nicht Bestandteil

Mobile Navigation, Breakpoints, Touch-Optimierung, Dashboard, neues
Frontend-Framework oder Backend-Refactoring.

## Ergebnis

Verbindliche Interaktionsregeln für die folgenden Seitenumbauten.
