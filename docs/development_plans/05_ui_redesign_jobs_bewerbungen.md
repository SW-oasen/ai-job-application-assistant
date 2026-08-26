# 05 – UI-Redesign: Jobs & Bewerbungen

## Ziel

Die Hauptseite `/` als kompakte Desktopübersicht vereinheitlichen. Kein
Ausbau zum späteren Statistik-/Schnellzugriffs-Dashboard.

## Verantwortung

Übersicht, Suche, Filter, Statusorientierung und Einstieg in Job-Detail.
Keine vollständige Profil- oder Jobbearbeitung.

## Zielstruktur

### Grundstruktur
Desktopbreite nutzen. Zwei spaltig. 
Links: 
Dashboardfunktion 
- Statisstikgraphik der Bewerbungsstati 
- Bewerbungsstatus-Buttons als Filter. Mehrfachauswahl erlaubt, dedeutet aber OR Relation
- Navigation zur Verwaltung und optional direkte Aktion zum Jobimport

Rechts: 
- Suchfeld oben
- Job-/Bewerbungsliste 

### Job-/Bewerbungsliste
kompakte Tabellen-/Zeilenstruktur

Mögliche bestehende Informationen: Jobtitel, Unternehmen, Bewerbungsstatus, offen/archiviert, Fit-Werte, Import-/Bewerbungsdatum,
letzte Aktivität und Link zum Detail. Keine neuen Statistikberechnungen nur für das Redesign.

## Filter

Bestehende Statusfilter und Stichwortsuche erhalten und kompakt als
Toolbar anordnen. Filterzustand beim Detailwechsel nur dann erhalten,
wenn dies ohne neue komplexe State-Infrastruktur möglich ist.

## Desktop-Optimierung

Volle Breite, geringe Zeilenhöhe, kompakte Status-Badges, keine Mobile-Karten, keine Breakpoint-Logik. Lange Titel sinnvoll umbrechen.

## Navigation

Konsistent: Jobs & Bewerbungen, Verwaltung, Job-Detail über Jobzeile öffnen.

## Regressionstests

Alle Jobs laden, Statusfilter, Stichwortsuche, offene/beworbene/archivierte Jobs soweit vorhanden, Detail öffnen,
Rückkehr, Status-/Fit-Anzeige, leere Listen und Ladefehler.

## Nicht Bestandteil

Profilvollständigkeit, Importlogik, Matchinglogik oder Mobile/Responsive.

## Akzeptanzkriterien

Schnelle Übersicht; Desktopbreite sinnvoll genutzt; Suche/Filter sofort erreichbar; kompakte Jobzeilen; eindeutiger Einstieg in Detail; bestehende Filter-/Statuslogik unverändert.
