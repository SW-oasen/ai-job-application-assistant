# Roadmap

Knappes Arbeitsprotokoll für die Weiterentwicklung. Nutzerhinweise stehen in
der [README](../README.md), technische Grundlagen im
[Architekturdokument](architecture.md).

## Aktuell

- Weitere unterschiedliche Stellenanzeigen als Testbasis importieren.
- Extraktion und Matching zunächst beobachten, noch nicht anhand einzelner
  Stellen weiter optimieren.
- Manuelle Soll-Bewertungen für ausgewählte Stellen in
  [evaluation.md](evaluation.md) festhalten.

## Als Nächstes

- Extraktion in Anforderungen, Tätigkeiten und Rahmenbedingungen trennen.
- Doppelte und unnötig fragmentierte Anforderungen reduzieren.
- Review-Integration abschließen: Dify-Workflows finalisieren, Migration und
  Konfiguration testen, Automatisierung der Review-Historie prüfen.

## Erledigt

- Verwaltungsoberfläche auf `/manage` als kompakter Desktop-Arbeitsbereich
  umgesetzt: Profil, Erfahrung & Skills, Projekte & Nachweise, Master-Profile
  und Jobimport.
- Profilressourcen mit direkt öffnenden Editoren und Schutz vor dem Verwerfen
  ungespeicherter Änderungen ausgestattet.
- Ausbildung, Zertifikate, Projekte, Referenzen und Skill-Evidenz in die
  direkte Verwaltungsoberfläche übernommen; Skills und Evidenz werden
  alphabetisch angezeigt.
- DE- und EN-Master-Profile mit unabhängiger Versionsauswahl und kompaktem,
  ein- und ausblendbarem Importfeld in die Verwaltung übernommen.
- Datenpflege beim Jobimport um Suche, Bewerbungsstatus und Matching-Filter
  erweitert; der angezeigte Status ist der Bewerbungsstatus.
- DE-/EN-Master-Profile importierbar und versioniert.
- CV-Recommender mit verÃ¶ffentlichtem Dify-Workflow, evidenzgebundener
  Validierung und versioniertem CV-Markdown umgesetzt.
- CV-Auswahl als vorausgewÃ¤hlte, abwÃ¤hlbare Buttons auf der Jobdetailseite;
  Referenzen bleiben optional.

- Profil, CV-Import, Jobimport und evidenzbasiertes Matching umgesetzt.
- Berufliche Ziele im Profil strukturiert erfassbar gemacht.
- Portfolio-Projekte mit geprüftem JSON-Import als eigene Evidenzquelle
  aufgenommen.
- Qualifikations-Fit und strukturierten Ziel-Fit getrennt bewertet und
  angezeigt.
- Deutsch-englische Begriffszuordnung für Vorhersagemodelle, Rohdatenanalyse,
  Datenbereinigung und Datenqualität ergänzt.
- Einträge im Bewerbungsverlauf löschbar gemacht; Status wird anschließend aus
  den verbleibenden Einträgen neu aufgebaut.
- Dashboard: offene Jobs unabhängig vom Matchingstatus zusammengefasst und
  Stichwortsuche ergänzt.
- Lokalen Webzugriff auf den Host begrenzt.

## Grundsätze

- Änderungen anhand mehrerer Referenzstellen statt einzelner Sonderfälle
  bewerten.
- Keine unbelegten Kompetenzen aus verwandten Begriffen ableiten.
- Projekt-, Ausbildungs- und Berufsevidenz unterscheidbar halten.
- Dokumentation knapp halten und erst bei Unübersichtlichkeit aufteilen.
