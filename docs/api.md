# Backend-API

Basisadresse auf dem Host: `http://localhost:8080`

Basisadresse aus Dify: `http://application-assistant-backend:8080`

## Bewerbungsverwaltung

- `GET /applications?profile_id={profile_id}` listet Bewerbungen.
- `POST /applications` legt eine Bewerbung mit Status, Datum und
  Kommunikationsweg an.
- `GET /applications/by-job/{job_id}?profile_id={profile_id}` liefert die
  Bewerbung und ihren Ereignisverlauf.
- `PATCH /applications/{application_id}` aktualisiert Status, Datum,
  Kommunikationsweg, Notiz oder nächste Aktion.
- `POST /applications/{application_id}/events` ergänzt ein Kommunikations-
  oder Verlaufsereignis.

## Health

```http
GET /health
```

## Matching

`GET /matching/context?job_id=<uuid>&profile_id=<uuid>` liefert den
gespeicherten, normalisierten Jobtext sowie die aus dem ausgewählten Profil
abgeleitete Evidenz. Referenzen und Kontaktdaten werden dabei nicht als
Matching-Evidenz ausgegeben.

## Bewerbungsdokumente

`POST /applications/document-context`

Erwartet `job_id`, `profile_id` und `language` (`de` oder `en`). Der Endpunkt
legt bei Bedarf eine Entwurfsbewerbung an und liefert den gespeicherten Job,
das profilbezogene Matching und kanonische Profilnachweise. Kontaktdaten und
Referenzen werden nicht an den Generierungsworkflow ausgegeben.

`POST /applications/{application_id}/documents`

Speichert einen erzeugten Dokumententwurf. Erlaubte Dokumenttypen sind
`profile_summary`, `cv_suggestions`, `project_selection`, `cover_letter`,
`application_questions` und `interview_preparation`. Die Versionsnummer wird
pro Bewerbung, Dokumenttyp und Sprache automatisch erhöht; vorhandene
Versionen werden nicht überschrieben.

`GET /applications/{application_id}/documents`

Listet alle gespeicherten Dokumentversionen der Bewerbung auf.

`POST /matching/evaluate` akzeptiert zusätzlich zu `job_id`, `requirements`
und optionaler externer `evidence` eine `profile_id`. Ist sie gesetzt, lädt das
Backend Skills, Berufserfahrung, Ausbildung und Zertifikate direkt aus der
kanonischen Profilverwaltung.

Die lesbare lokale Auswertung ist unter
`http://localhost:8080/matching/admin` erreichbar. Sie verwendet:

- `GET /matching/jobs` für die Jobauswahl,
- `GET /matching/results?job_id=<uuid>&profile_id=<uuid>` für bereits
  persistierte, profilspezifische Ergebnisse.

## URL importieren

```http
POST /imports/url
Content-Type: application/json

{
  "url": "https://example.com/job/123",
  "force_browser": false
}
```

Die Antwort trennt das unveränderte `raw_html` vom bereinigten `markdown`.
`quality_sufficient` zeigt an, ob die konfigurierten Qualitätsregeln erfüllt
sind. `browser_fallback_recommended` wird bei zu kurzem Inhalt, fehlendem Titel
oder Anzeichen einer Login-/Bot-Schutzseite gesetzt.

Bei `force_browser=true` wird Chromium direkt verwendet. Ohne dieses Flag
startet das Backend zunächst den schlankeren HTTP-Import und wechselt
automatisch zu Chromium, wenn der Inhalt die Qualitätsprüfung nicht besteht
oder dynamisch geladen werden muss.

Sicherheitsgrenzen:

- nur `http` und `https`
- keine eingebetteten Zugangsdaten
- lokale, private und reservierte Zieladressen sind blockiert
- jedes Redirect-Ziel wird erneut validiert
- konfigurierbares Timeout, Redirect- und Downloadlimit
- ausschließlich HTML und Klartext
- Browser-Subrequests werden ebenfalls auf öffentliche HTTP(S)-Ziele begrenzt

Beispiel:

```powershell
$body = @{
  url = "https://example.com/job/123"
  force_browser = $false
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8080/imports/url `
  -ContentType application/json `
  -Body $body
```

## PDF importieren

```http
POST /imports/pdf
Content-Type: multipart/form-data
```

Das Backend prüft MIME-Typ, PDF-Signatur und Dateigröße und berechnet einen
SHA-256-Hash. Textbasierte PDFs werden lokal verarbeitet. Nur wenn deren Text
die Qualitätsprüfung nicht besteht, wird MinerU mit `parse_method=ocr`
aufgerufen.

```powershell
curl.exe -X POST http://localhost:8080/imports/pdf `
  -F "file=@C:\path\to\job.pdf;type=application/pdf"
```

Die Antwort nennt `extraction_method` (`native_pdf` oder `mineru`) und bei
MinerU-Verarbeitung zusätzlich die Task-ID, sofern der Dienst sie liefert.

## HTML/SingleFile importieren

```http
POST /imports/html
Content-Type: multipart/form-data
```

Akzeptiert gespeicherte `.html`- und `.htm`-Dateien, einschließlich
Firefox-SingleFile. HTML wird direkt lokal bereinigt und in Markdown
umgewandelt. Skripte, Frames und Formulare werden nicht ausgeführt; externe
Ressourcen werden nicht nachgeladen. MinerU wird für HTML nicht verwendet.
