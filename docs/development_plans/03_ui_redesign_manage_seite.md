# 03 – UI-Redesign: Verwaltung

## Ziel

`/manage` von der verschachtelten Verwaltungsoberfläche mit iframe zu
einem kompakten Desktop-Arbeitsbereich umbauen. Die normalen
Verwaltungsabläufe sind direkt erreichbar; API-/Diagnosefunktionen dürfen
außerhalb des täglichen Workflows bestehen bleiben.

## Aktueller Funktionsumfang

Mindestens Profilbearbeitung per iframe, Stellenimport,
Browser-Import-Einrichtung, URL-Import, PDF-/HTML-/SingleFile-Import,
PDF-Reimport und Datenpflege/Löschen von Jobs. Die Profilverwaltung
enthält zusätzlich Stammdaten, Ziele, Skills/Evidenz, Erfahrung,
Ausbildung/Zertifikate, Projekte, Referenzen, Master-Profile und
bestehende CV-Import-/Vorschlagsfunktionen.

## Zielstruktur

Empfohlene Haupttabs:

`[ Profil ] [ Erfahrung & Skills ] [ Projekte & Nachweise ] [ Master-Profile ] [ Jobimport ]`

Die Benennung darf nach vollständiger Inventur angepasst werden; die
Top-Level-Navigation soll aber deutlich kürzer als heute werden.

### Profil

Basisdaten/Kontakt, berufliche Ziele/Zielprofil, Sprachen und ggf.
Ausbildung/Zertifikate.

### Erfahrung & Skills

Berufserfahrung, Activity-Bullets, Skills und Skill-Evidenz. Wo sinnvoll
Liste links und Bearbeitung rechts.

### Projekte & Nachweise

Portfolio-Projekte, Referenzen und ggf. Import-Vorschläge.

### Master-Profile

DE und EN als kompakte Karten nebeneinander: aktuelle Version, neue
Version importieren, anzeigen, Versionshistorie. Keine Synchronisation
mit strukturierten Profildaten einführen.

### Jobimport

Browser-Import-Aktion, URL-Import, Dateiimport PDF/HTML, Importstatus
und Datenpflege. URL- und Dateiimport können nebeneinander stehen.

## Umsetzungsstand

Abgeschlossen:

- fünf kompakte Hauptbereiche: Profil, Erfahrung & Skills, Projekte &
  Nachweise, Master-Profile und Jobimport;
- nahezu volle Desktopbreite sowie zweispaltige Arbeitsbereiche;
- aufklappbare Eintragseditoren mit Schutz vor dem Verwerfen ungespeicherter
  Änderungen;
- getrennte, unabhängig anzeigbare DE- und EN-Master-Profile mit
  Versionsauswahl und einklappbarem Importfeld;
- Datenpflege mit Suche, Bewerbungsstatus und Matching-Filter;
- keine sichtbaren iframe- oder Übergangshinweise im normalen Workflow.

Bewusst nicht Teil der neuen Oberfläche: direkter CV-Import und getrennte
DE/EN-Lokalisierungen einzelner Ressourcen. Der CV-Import bleibt als
Backend-/Diagnosefunktion verfügbar. Die Lokalisierungen werden erst bei
konkretem Bedarf wieder aufgegriffen; zunächst werden Extraktion und Review
beobachtet und verbessert.

## iframe-Migration

1.  Funktionen/API-Aufrufe der eingebetteten Profilverwaltung
    vollständig erfassen.
2.  Neue Tab-/Kartenstruktur anlegen, ohne Funktionen zu entfernen.
3.  Profilbereiche schrittweise übernehmen und jeweils testen.
4.  Master-Profile übernehmen und Versionierung testen.
5.  Jobimport kompakt integrieren.
6.  Sichtbaren iframe und Übergangshinweise entfernen. API- und
    Diagnosefunktionen können bestehen bleiben.

## Breitenstrategie

Nahezu volle Desktopbreite. Listen und Editoren bevorzugt nebeneinander.
Keine Vollbreitenkarte für wenige kurze Felder. Lange
Markdown-/Beschreibungstexte dürfen breiter sein. Vertikale Abstände
reduzieren.

## Regressionstests

Profil/Basisdaten, Ziele, Skills, Evidenz, Erfahrung/Activity-Bullets,
Ausbildung/Zertifikate, Projekte, Referenzen, Master-Profil DE/EN
inklusive Versionen, bestehende CV-Import-/Vorschlagsfunktionen,
URL-Import, HTML/SingleFile, PDF, PDF-Reimport, Browser-Import-Link, Job
löschen und alle Meldungszustände testen.

## Nicht Bestandteil

Datenmodelländerungen, Masterprofil-Synchronisation,
CV-Recommender-Änderungen, Matching, Dashboard oder Mobile/Responsive.

## Akzeptanzkriterien

Die direkten Verwaltungsfunktionen bleiben erreichbar; iframe ist für den
normalen Workflow nicht mehr nötig; Top-Level-Navigation ist kürzer;
Desktopbreite wird besser genutzt; typische Wege benötigen weniger Scrollen.
