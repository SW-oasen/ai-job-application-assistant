# 01 – UI-Redesign: Informationsarchitektur

## Ziel

Vor dem visuellen Umbau wird die Informationsarchitektur verbindlich
festgelegt. Bestehende Funktionen dürfen durch das Redesign weder
verschoben noch unbemerkt verändert oder entfernt werden.

## Architekturentscheidung: Desktop-only

- Lokale, datenintensive Desktop-Webanwendung.
- Kein Mobile- oder Responsive-Design als Ziel.
- Verfügbare Displaybreite konsequent nutzen; keine schmale zentrale
  `max-width` als Standard.
- Mehrspaltige Darstellungen bevorzugen, wenn sie vertikales Scrollen
  reduzieren.
- Tabellen, Formulare und Detailansichten für typische Desktopbreiten
  optimieren.
- Bestehende Responsive-Regeln können nach erfolgreicher
  Desktop-Migration entfernt werden.

## Fachliche Hauptbereiche

1.  **Jobs & Bewerbungen** (`/`) – Übersicht, Suche, Filter, Status und
    Einstieg in konkrete Jobs.
2.  **Verwaltung** (`/manage`) – globale Stammdaten, Master-Profile und
    Importwerkzeuge.
3.  **Job-Detail** (`/jobs/{job_id}`) – alle Funktionen für eine
    konkrete Stelle und Bewerbung.

Browser-Import und Profil-Admin sind technische/spezialisierte Routen,
keine zusätzlichen fachlichen Hauptbereiche.

## Jobs & Bewerbungen

Dorthin gehören Jobübersicht, Bewerbungsstatus, Suche, Filter und
Einstieg in Job-Detail. Nicht dorthin gehören globale Profilpflege,
CV-Empfehlungsdetails oder umfangreiche Jobanalyse.

## Verwaltung

Dorthin gehören Profil/Basisdaten, berufliche Ziele, Skills und Evidenz,
Berufserfahrung und Activity-Bullets, Ausbildung/Zertifikate, Projekte,
Referenzen, Master-Profile DE/EN, bestehende
Import-Vorschläge/CV-Import-Funktionen sowie Stellenimport per
URL/PDF/HTML und Browser-Import-Einrichtung.

Die bestehende Profilverwaltung per iframe ist eine Übergangslösung und
keine Zielarchitektur.

## Job-Detail

Dorthin gehören Job-Metadaten, Original-/Quelldaten zur
Extraktionskontrolle, extrahierte Informationen, Matching/Evidenz,
Qualifikations-Fit und Ziel-Fit, Bewerbungsstatus und Ereignisverlauf,
archivierte Unterlagen, CV-Empfehlung/CV-Versionen und später
Anschreiben.

Die CV-Empfehlung bleibt ausdrücklich jobbezogen, da sie aus
`konkrete Stelle × Master-Profil` entsteht.

## Späteres Dashboard

Nicht Teil dieses Redesigns. Es kann später unabhängig ergänzt werden,
z. B. mit offenen Stellen, beworbenen offenen Stellen, Statistiken,
offenen Profilpunkten, letzten Aktivitäten, Schnellzugriffen und
Einstiegshilfe.

## Leitprinzipien

- Fachliche Zuständigkeit vor Optik.
- Bestehende Workflows erhalten.
- Globale Daten → Verwaltung.
- Stellenabhängige Funktionen → Job-Detail.
- Übersicht → Jobs & Bewerbungen.
- Seltene Details dürfen eingeklappt werden.
- Häufige Aktionen ohne lange Scrollwege erreichbar machen.
- Breite statt Länge: Desktopfläche mit Spalten, Karten und kompakten
  Tabellen nutzen.
- Keine gleichzeitige fachliche Optimierung von Extraktion, Matching
  oder CV-Recommender.

## Vorgehen vor jeder Umsetzung

1.  Vorhandene Funktionen und Aktionen inventarisieren.
2.  Verwendete API-Endpunkte dokumentieren.
3.  Zustände, DOM-Abhängigkeiten und Lazy Loading identifizieren.
4.  Zielposition jeder Funktion festlegen.
5.  Erst danach Markup/Layout ändern.

## Stop-Kriterium

Wenn unklar ist, ob ein UI-Element nur Darstellung oder Teil eines
fachlichen Workflows ist, nicht entfernen. Zuerst Funktion und
API-Nutzung prüfen.

## Ergebnis

Nach diesem Schritt steht die fachliche Seitenzuordnung fest. Noch keine
CSS-/Layoutänderung durchführen.
