# Entwicklungsplan – Cover-Letter-Generierung

## Ziel

Automatische, stellenbezogene Generierung eines individuellen Anschreibens auf Basis der bereits gespeicherten Jobdaten und des versionierten Masterprofils. Die Umsetzung erfolgt **nach Abschluss der CV-Generierung**. Die Siemens-Energy-Bewerbung wird zunächst noch manuell erstellt; die neue Funktion soll zuerst mit weniger wichtigen Bewerbungen getestet werden.

## 1. Voraussetzungen

- CV-Generierung vollständig abschließen und stabilisieren.
- Bestehende Job-Extraktion und Job-Matching weiterverwenden.
- Versioniertes deutsches/englisches Masterprofil als einzige Profilquelle verwenden.
- Keine zweite parallele Datenpflege für Anschreiben einführen.

## 2. Cover-Letter-Spezifikation

Eine versionierte Generierungsspezifikation einführen, kein starres Texttemplate.

Vorgesehene semantische Bausteine:

- Anrede
- Einstieg und konkrete Motivation für Rolle/Aufgabe
- stärkster fachlicher Bezug zur Stelle
- konkrete Evidenz aus Berufserfahrung und/oder Projekten
- Transfer der bisherigen Erfahrung auf die Zielrolle
- kurzer Ausblick/Motivation für den nächsten Schritt
- Schlussformel

Regeln:

- maximal eine Seite
- typischerweise 4–5 Textabsätze plus Anrede und Gruß
- Bausteine dürfen sinnvoll zusammengeführt werden
- keine Überschriften im fertigen Anschreiben
- keine erfundenen Kompetenzen oder Erfahrungen
- keine bloße Wiederholung des Lebenslaufs
- 2–3 wichtigste Anforderungen priorisieren statt die Stellenanzeige vollständig abzuhaken
- konkrete Evidenz vor allgemeinen Behauptungen
- fehlende Anforderungen nicht defensiv aufzählen
- keine generischen KI-/Bewerbungsfloskeln
- Sprache der Stellenanzeige verwenden, sofern nicht manuell überschrieben

## 3. Datenbasis für die Generierung

Input für den Generator:

- strukturierte Job-Metadaten
- Tätigkeiten und Anforderungen der Stellenanzeige
- Ergebnis des Job-Matchings
- aktuelles versioniertes Masterprofil
- relevante Berufserfahrungen
- relevante Skills
- ausgewählte Projekte und deren Evidenz
- optional Ansprechpartner, falls vorhanden
- optional manuelle Hinweise zur Bewerbung

Der Generator soll nur belegte Inhalte aus diesen Quellen verwenden.

## 4. Evidenzauswahl

Vor der eigentlichen Textgenerierung einen separaten Auswahl-/Planungsschritt einführen:

1. wichtigste 2–3 Anforderungen der Stelle bestimmen
2. passende Profil-Evidenz je Anforderung auswählen
3. stärkste Argumentationslinie festlegen
4. redundante CV-Inhalte aussortieren
5. Ergebnis als strukturierten Generierungsplan an das LLM übergeben

Beispielstruktur intern:

```json
{
  "motivation_focus": "...",
  "key_requirements": ["...", "..."],
  "evidence": [
    {
      "requirement": "...",
      "source_type": "professional|project|skill",
      "source": "...",
      "argument": "..."
    }
  ],
  "transfer_argument": "...",
  "closing_focus": "..."
}
```

## 5. Generierung

- LLM erhält Stellenprofil, ausgewählte Evidenz, Masterprofil und Cover-Letter-Spezifikation.
- Ausgabe zunächst als Markdown.
- Keine direkte PDF-Erzeugung im ersten Schritt.
- Generierten Text zusammen mit verwendeten Quellreferenzen/Evidenzen speichern.
- Prompt-/Spezifikationsversion und verwendete Masterprofilversion protokollieren.

## 6. Validierung

Nach der Generierung automatische Prüfung:

- enthält jede fachliche Behauptung belegbare Profilevidenz?
- wurden nicht vorhandene Technologien oder Erfahrungen ergänzt?
- passt das Anschreiben zur konkreten Stelle?
- enthält es unnötige Wiederholungen aus dem CV?
- sind Unternehmensname, Rolle und Ansprechpartner korrekt?
- passt die Sprache?
- liegt die Länge innerhalb des definierten Rahmens?

Bei Problemen Ergebnis markieren und nicht automatisch freigeben.

## 7. GUI

Im Bewerbungs-/Jobdetailbereich ergänzen:

- `Anschreiben generieren`
- Auswahl der Masterprofil-Version
- optionales Feld `Hinweise für Anschreiben`
- Vorschau des generierten Markdown-Texts
- `Neu generieren`
- `Bearbeiten`
- `Freigeben`
- später: Export als PDF

Generierung erst aktivieren, wenn ein Bewerbungsstatus bzw. eine konkrete Bewerbung vorhanden ist.

## 8. Versionierung und Speicherung

Für jedes generierte Anschreiben speichern:

- Bewerbung/Job-ID
- Sprache
- Masterprofil-Version
- Cover-Letter-Spezifikationsversion
- Prompt-/Generatorversion
- verwendete Evidenzen
- generierter Markdown-Text
- Bearbeitungsstand
- Freigabestatus
- Zeitstempel

Manuelle Änderungen dürfen eine neue Dokumentversion erzeugen; ältere Versionen bleiben erhalten.

## 9. Teststrategie

Zunächst keine wichtigen Zielbewerbungen automatisiert erzeugen.

Testreihenfolge:

1. 3–5 weniger wichtige, aber realistische Stellen verwenden.
2. Generierung mit manuell erstellten Anschreiben bzw. eigener Qualitätsbewertung vergleichen.
3. Typische Fehler sammeln: Floskeln, CV-Wiederholung, falsche Evidenz, Übertreibung, zu generische Motivation.
4. Spezifikation und Auswahlalgorithmus iterativ verbessern.
5. Erst nach stabiler Qualität für wichtige Bewerbungen verwenden.

## 10. Umsetzungsreihenfolge

1. CV-Generierung fertigstellen.
2. Cover-Letter-Spezifikation und Datenmodell ergänzen.
3. Evidenzauswahl/Generierungsplan implementieren.
4. Markdown-Generierung implementieren.
5. automatische Validierung ergänzen.
6. GUI und Versionierung anbinden.
7. mit weniger wichtigen Stellen testen.
8. nach erfolgreicher Evaluation PDF-Export und produktiven Einsatz ergänzen.

## Abgrenzung für Version 1

Noch nicht umsetzen:

- vollautomatisches Absenden von Bewerbungen
- automatische Kontaktaufnahme mit Recruitern
- mehrere Design-/Layoutvarianten
- komplexe Unternehmensrecherche außerhalb der Stellenanzeige
- automatische Optimierung anhand von Bewerbungserfolgen
