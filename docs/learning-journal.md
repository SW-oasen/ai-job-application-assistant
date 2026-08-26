# Lernprotokoll

Kurze Notizen zu Beobachtungen und daraus abgeleiteten Entscheidungen. Details
zu geplanten Arbeiten stehen in der [Roadmap](roadmap.md).

## 2026-07 – Matching mit deutschen Anforderungen

- Beobachtung: Vorhandene englische Skills wurden bei deutschen Anforderungen
  teilweise als Lücken bewertet.
- Änderung: Kleine, kontrollierte Begriffsgruppen für häufige Synonyme und
  deutsche Komposita ergänzt.
- Ergebnis: Offensichtliche False Positives wurden reduziert.
- Erkenntnis: Einzelkorrekturen reichen nicht; Extraktion, Fragmentierung und
  Matching müssen mit mehreren Stellen gemeinsam bewertet werden.

## 2026-07 – Nächste Ausbaustufe

- Portfolio-Projekte sollen als belegbare praktische Erfahrung einfließen.
- Tätigkeiten einer Stelle sollen zusätzlich mit den persönlichen Zielen
  verglichen werden.
- Entscheidung: Qualifikations-Fit und Ziel-Fit bleiben getrennte Aussagen.

## 2026-07 – Review-Integration und Fehlerhärtung

- Beobachtung: Dify-Workflows lieferten zum Teil fehlerhafte oder anders
  formatierte Antworten (z. B. numerische `attempt`-Felder), die Persistenz
  oder Nachverarbeitung störten.
- Änderung: Review-Läufe als optional und nicht-blockierend implementiert;
  fehlerhafte Reviews werden in der Review-Historie protokolliert, ohne den
  Import oder das Matching abzubrechen.
- Erkenntnis: Exakte Feldtypen (z. B. `attempt` als String) und valide API-
  Keys sind entscheidend; Migration der Review-Tabellen ist nach Workflow-
  Import erforderlich.

## 2026-08 – CV-Recommender und Master-Profile

- DE-/EN-Master-Profile werden importiert, versioniert und als einzige
  Kandidatenquelle für die CV-Empfehlung verwendet.
- Der veröffentlichte Dify-Workflow erzeugt eine strukturierte, belegbare
  Empfehlung; das Backend validiert IDs und rendert versioniertes CV-Markdown.
- Die Jobdetailseite verwendet vorausgewählte Button-Auswahlen; Referenzen
  sind optional, Aktivitäts-Bullets bleiben in der Verwaltung.
- Workflow-Änderungen müssen in Dify nach dem Import veröffentlicht werden;
  ein Entwurf ist über die Workflow-API nicht ausführbar.

## 2026-08 – Verwaltungsoberfläche

- Beobachtung: Die bisherige, eingebettete Profilverwaltung benötigte für
  zusammenhängende Pflegevorgänge zu viele Wechsel und zu viel vertikalen
  Platz.
- Änderung: Die normale Pflege liegt nun direkt in `Verwaltung` in fünf
  Bereichen. Desktop-Listen und Editoren nutzen zwei Spalten, neue Einträge
  öffnen ihren Editor direkt am jeweiligen Bereich.
- Entscheidung: Beim Wechsel oder Schließen eines geänderten Editors wird
  nach dem Speichern gefragt. Die Ablehnung verwirft ausschließlich die
  Änderungen und führt den gewünschten Wechsel trotzdem aus.
- Entscheidung: Einzelne Ressourcen werden zunächst als kanonischer Text
  gepflegt. Getrennte DE/EN-Lokalisierungen werden erst bei beobachtbaren
  Matchingproblemen erneut bewertet; zuerst werden Extraktion und Review
  verbessert.
- Entscheidung: Der Masterprofil-Import ist der reguläre Einstieg für DE und
  EN. Der CV-Import bleibt als Backend-/Diagnosefunktion erhalten, aber nicht
  als sichtbarer täglicher Workflow.
