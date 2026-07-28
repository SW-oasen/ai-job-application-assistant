# Profilverwaltung

## Lokale Oberfläche

Die Profilverwaltung ist nach dem Start des Backends hier erreichbar:

```text
http://localhost:8080/profiles/admin
```

Zum ersten Test:

1. Mit `Neues Profil` ein Profil anlegen.
2. Links einen der fünf Bereiche auswählen.
3. Mit `Eintrag hinzufügen` einen Datensatz erfassen.
4. Deutsche und englische Texte getrennt pflegen.
5. Den Eintrag zunächst als `Entwurf` speichern und nach Prüfung auf
   `Freigegeben` setzen.
6. Über `Revisionen` den unveränderlichen Änderungsverlauf prüfen.

Leere Sprachfassungen sind erlaubt und können später ergänzt werden.
Referenzdaten sollten nur mit dokumentierter Nutzungseinwilligung freigegeben
werden. Die Oberfläche ist derzeit eine lokale Entwicklungsoberfläche ohne
Anmeldung und darf nicht öffentlich bereitgestellt werden.

Die Profilverwaltung ist die kanonische, editierbare Faktenbasis für Matching
und spätere Dokumenterzeugung. Angepasste CVs und Profiltexte sind keine
Profilquelle.

Das Profil selbst enthält editierbare, weitgehend stabile Stammdaten:

- vollständiger Name,
- Nationalität,
- Telefon und E-Mail,
- LinkedIn-, GitHub- und Portfolio-Link.

Stellenbezogene Profilzusammenfassungen und Berufsbezeichnungen aus einem
angepassten CV werden nicht als Stammdaten übernommen.

## Unterstützte Bereiche

- Skills
- Berufserfahrungen
- Ausbildungen
- Zertifikate
- Referenzen

## Skill-Taxonomie

Skill-Kategorien und Kenntnisniveaus sind zentral definiert und werden nicht
als Freitext gespeichert. Die Profiloberfläche, CV-Importe und spätere
Portfolio-Importe verwenden dadurch dieselben stabilen Werte.

Kategorien:

- Programmiersprachen
- Frameworks & Bibliotheken
- Daten, KI & Machine Learning
- Datenbanken
- Cloud & DevOps
- Tools & Plattformen
- Methoden & Prozesse
- Soziale Kompetenzen
- Fach- & Branchenwissen
- Sprachen
- Sonstiges

Kenntnisniveaus:

- Grundkenntnisse
- Gute Kenntnisse
- Fortgeschritten
- Experte / Expertin

Die Definition ist über `GET /profiles/taxonomy/skills` verfügbar. In der
Datenbank werden stabile englische Codes gespeichert; die Oberfläche zeigt
verständliche deutsche Bezeichnungen.

Jeder Bereich unterstützt deutsche und englische Lokalisierungen. Inhalte
beginnen standardmäßig als `draft` und können nach Prüfung auf `approved`
gesetzt werden.

## Revisionen

Jede Anlage oder Änderung erhöht die Revision des Eintrags und die
Gesamtrevision des Profils. Zusätzlich wird ein unveränderlicher Snapshot in
`profile_entity_revisions` gespeichert. `change_reason` dokumentiert den
fachlichen Anlass.

Einträge werden nicht durch CV-Importe oder LLM-Ausgaben automatisch geändert.

## API

Ein Profil wird über `POST /profiles` angelegt. Die Ressourcen liegen darunter:

```text
/profiles/{profile_id}/skills
/profiles/{profile_id}/experiences
/profiles/{profile_id}/education
/profiles/{profile_id}/certificates
/profiles/{profile_id}/references
```

`GET` listet Einträge, `POST` legt sie an und `PATCH` aktualisiert sie. Skills
werden über `active: false` deaktiviert und nicht hart gelöscht.

Der Änderungsverlauf eines Eintrags ist verfügbar unter:

```text
GET /profiles/{profile_id}/revisions/{entity_type}/{entity_id}
```

Referenz-Kontaktdaten sind sensible Daten. Eine Weitergabe an Dify oder ein LLM
darf später nur bei `usage_consent: true` und für einen ausdrücklich
freigegebenen Anwendungsfall erfolgen.

## CV-Import und kontrollierte Übernahme

Ein CV überschreibt das kanonische Profil nicht. Der Import läuft über einen
Prüfpuffer:

```text
Dify import CV → strukturiertes CV → CV-Vorschläge → Prüfen → Übernehmen/Ignorieren
```

In der Oberfläche befindet sich dafür der Bereich `CV-Vorschläge`. Bis der
Dify-Workflow den Backend-Aufruf selbst enthält, kann dessen vollständiges
`structured_cv`-Ergebnis über `Dify-JSON importieren` eingefügt werden. Daraus
entstehen automatisch einzelne Vorschläge für Skills, Berufserfahrung,
Ausbildung, Zertifikate und Referenzen.

Offene Vorschläge können einzeln geprüft oder über die Kontrollkästchen
gesammelt übernommen beziehungsweise ignoriert werden. Die Sammelübernahme
ist nur für Vorschläge ohne erkannten Konflikt zulässig und verwendet die
unveränderten vorgeschlagenen Daten.

Vorhandene Profildaten werden anhand stabiler fachlicher Schlüssel erkannt:

- Skills: normalisierter Name,
- Berufserfahrung: Unternehmen und lokalisierter Stellentitel,
- Ausbildung: Institution und lokalisierter Abschluss,
- Zertifikate: offizieller Name und Aussteller,
- Referenzen: bevorzugt E-Mail, ersatzweise Name und Organisation,
- Profilstammdaten: das ausgewählte Zielprofil.

Ein in allen vorgeschlagenen Feldern identischer Treffer wird als `Duplikat`
markiert. Abweichende Werte am selben fachlichen Eintrag werden als `Konflikt`
markiert. Beides muss einzeln geprüft werden. Die Oberfläche zeigt bestehenden
Stand und CV-Vorschlag nebeneinander und verlangt eine ausdrückliche Auflösung:

- bestehenden Eintrag behalten,
- CV-Werte in den bestehenden Eintrag übernehmen,
- bei Berufserfahrung, Ausbildung, Zertifikat oder Referenz als separaten
  Eintrag anlegen.

Für Profilstammdaten und Skills ist ein separater Eintrag nicht erlaubt.
Dadurch entstehen insbesondere keine doppelten Skills. Ohne gewählte
Konfliktauflösung lehnt das Backend die Übernahme mit HTTP 409 ab.

Profilzusammenfassungen werden nicht als kanonische Fakten übernommen.

Enthält der CV stabile Profilstammdaten, erzeugt der Adapter dafür einen
separaten Vorschlag vom Typ `profile`. Beim Übernehmen wird ausschließlich das
zuvor ausgewählte Zielprofil aktualisiert. Leere CV-Felder überschreiben keine
vorhandenen Stammdaten.
Referenzen erhalten beim Import immer `usage_consent: false`. Ungenaue oder
nicht normalisierte Datumsangaben müssen vor der Übernahme im Vorschlags-JSON
korrigiert werden.

Der Backend-Adapter für den Dify-Workflow lautet:

```text
POST /profiles/{profile_id}/cv-imports/structured
```

Beispiel für den Body eines Dify-HTTP-Knotens:

```json
{
  "source_filename": "lebenslauf.pdf",
  "source_language": "de",
  "structured_cv": {
    "profile": {},
    "skills": {"categories": [], "languages": []},
    "work_experience": [],
    "education": [],
    "certificates": [],
    "references": []
  }
}
```

Der direkte Vorschlagsvertrag für andere Importquellen ist:

```text
POST /profiles/{profile_id}/cv-imports
GET  /profiles/{profile_id}/cv-imports
POST /profiles/{profile_id}/cv-suggestions/{suggestion_id}/apply
POST /profiles/{profile_id}/cv-suggestions/{suggestion_id}/reject
```

### PDF direkt aus der Profilverwaltung importieren

Im Bereich `CV-Vorschläge` öffnet `Neu` den PDF-Import. Die Oberfläche sendet
die Datei an das Backend; nur das Backend kommuniziert mit der Dify Service
API. Dadurch wird der Dify-App-Schlüssel niemals an den Browser ausgeliefert.

Voraussetzungen:

1. `import_cv_pdf.yml` in Dify importieren, testen und veröffentlichen.
2. Auf der API-Zugangsseite dieser Dify-App einen App-API-Schlüssel erzeugen.
3. Den Schlüssel ausschließlich in der lokalen, ignorierten `.env` setzen:

   ```env
   DIFY_CV_WORKFLOW_API_KEY=app-...
   ```

4. Das Application-Assistant-Backend neu starten.

Der Backend-Endpunkt lautet:

```text
POST /profiles/{profile_id}/cv-imports/pdf
```

Er akzeptiert `multipart/form-data` mit `file` und `source_language`. Das
Backend lädt genau eine PDF zu Dify hoch und startet den veröffentlichten
Workflow mit der ausgewählten Profil-ID. Der strukturierte JSON-Import bleibt
in der Oberfläche als Diagnose- und Fallbackweg verfügbar.

## Portfolio-Grenze

Etappe 1 enthält keinen Portfolio-Connector und nimmt keinerlei Änderungen am
Portfolio-Repository vor. Die spätere Integration wird ausschließlich lesend
auf die festgelegten GitHub-Dateien zugreifen.
