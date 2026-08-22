# Evaluation

Knappe Referenz für die spätere Prüfung von Extraktion und Matching. Die Datei
wird erst mit mehreren importierten Stellen schrittweise ergänzt.

## Prüfumfang

- Anforderungen vollständig und ohne unnötige Duplikate
- Tätigkeiten getrennt von Anforderungen erkannt
- Muss-, Soll- und optionale Kriterien korrekt eingeordnet
- vorhandene Evidenz gefunden und mit passendem Kontext angezeigt
- echte Lücken nicht durch lose verwandte Skills verdeckt
- Qualifikations-Fit und Ziel-Fit nachvollziehbar getrennt

Der Ziel-Fit bewertet Rollen, Branchen, Orte, Arbeitsmodelle und
Beschäftigungsarten ausschließlich gegen die strukturierten Profilpräferenzen.
Bei befristeten Stellen wird die strukturierte Mindestlaufzeit aus dem Profil
in Monaten berücksichtigt. Unbefristete und befristete Anstellungen können
gleichzeitig als zulässige Beschäftigungsarten hinterlegt werden.
Freie Ausschlusskriterien werden nur bei eindeutig strukturierten Treffern
automatisch als Konflikt gewertet; textlich ähnliche Fälle bleiben manuell zu
prüfen.

Die Ziel-Fit-Gewichtung lautet:

- Tätigkeits-Fit: 35
- Beschäftigungsarten einschließlich Mindestlaufzeit bei Befristung: 30
- Seniorität: 20
- Zielort: 15
- Zielbranche: 10
- Arbeitsmodell: 10
- Zielrolle: 2 bis 10, abhängig von der hinterlegten Priorität

Unbekannte Stellenmerkmale werden nicht in die gewichtete Ziel-Fit-Quote
einbezogen.

Der Qualifikations-Fit wird zusätzlich als gewichtete Gesamtprozentzahl
ausgegeben:

- Muss-Anforderung: Gewicht 3
- Soll-Anforderung: Gewicht 2
- optionale Anforderung: Gewicht 1
- starker Match: 100 Prozent Erfüllung
- teilweiser Match: 65 Prozent
- übertragbare Erfahrung: 40 Prozent
- Lücke oder unklare Anforderung: 0 Prozent

Die Gesamtzahl ist die Summe der erreichten gewichteten Punkte geteilt durch
die maximal möglichen Punkte. Sie ersetzt nicht die Einzelbewertungen und
deren Evidenz.

## Gemeinsames Fazit

Aus Qualifikations-Fit, Ziel-Fit, unbelegten Muss-Anforderungen und
strukturiert erkannten Ausschlusskriterien wird eine regelbasierte Empfehlung
abgeleitet. Mögliche Ergebnisse sind `Bewerbung empfohlen`,
`Bewerbung erwägen`, `Manuell abwägen` und `Nicht priorisieren`.

Für diese Zusammenführung ist kein zusätzlicher KI-Workflow erforderlich.
Die Regelentscheidung bleibt dadurch reproduzierbar und anhand der beiden
Teilbewertungen nachvollziehbar. Ein späterer semantischer Workflow kann
unklare Freitextkriterien erläutern, darf die strukturierte Entscheidung aber
nicht stillschweigend überschreiben.

## Referenzstellen

| Stelle | Extraktion geprüft | Matching geprüft | Notiz |
|---|---:|---:|---|
| Slected.me GmbH – Data Scientist | teilweise | teilweise | Begriffszuordnung verbessert; Fragmentierung erneut prüfen |

## Offene Beobachtungen

- Nach erneuter Extraktion werden mehr Anforderungen als zuvor angezeigt.
- Mindestens mehrere weitere Stellen sind nötig, bevor Regeln angepasst werden.
