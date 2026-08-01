# Backend-API

Basisadresse auf dem Host: `http://localhost:8080`

Basisadresse aus Dify:
`http://application-assistant-backend:8080`

In der Entwicklungsumgebung steht die interaktive OpenAPI-Dokumentation unter
`http://localhost:8080/docs` bereit.

## Health

- `GET /health`

## Bewerbungen und Verlauf

- `GET /applications?profile_id={profile_id}`
- `POST /applications`
- `GET /applications/by-job/{job_id}?profile_id={profile_id}`
- `GET /applications/{application_id}`
- `PATCH /applications/{application_id}`
- `POST /applications/{application_id}/events`
- `PATCH /applications/{application_id}/events/{event_id}`
- `DELETE /applications/{application_id}/events/{event_id}`

Nach Bearbeiten oder Löschen eines Ereignisses wird der Bewerbungszustand aus
dem verbleibenden Verlauf neu aufgebaut.

## Archivierte Bewerbungsdateien

- `POST /applications/{application_id}/files`
- `GET /applications/{application_id}/files`
- `GET /applications/{application_id}/files/{file_id}/content`
- `DELETE /applications/{application_id}/files/{file_id}`

Akzeptiert werden PDF-Dateien innerhalb des konfigurierten Größenlimits. Die
Dateien liegen im Docker-Volume; PostgreSQL speichert Metadaten und Zuordnung.

## Generierte Dokumententwürfe

- `POST /applications/document-context`
- `POST /applications/{application_id}/documents`
- `GET /applications/{application_id}/documents`

Der Kontextendpunkt liefert Job, profilspezifisches Matching und kanonische
Profilnachweise. Kontaktdaten und Referenzen werden nicht an den
Generierungsworkflow ausgegeben.

## Jobimport

- `POST /imports/url`
- `POST /imports/pdf`
- `POST /imports/html`
- `POST /imports/browser-capture`
- `POST /imports/jobs/{job_id}/reimport`

URL-Importe akzeptieren nur öffentliche HTTP(S)-Ziele. Eingebettete
Zugangsdaten sowie lokale, private und reservierte Adressen werden blockiert.
Redirects und Browser-Subrequests werden erneut validiert. `browser-capture`
nimmt Seiteninhalt vom Browser-Lesezeichen unter `/browser-import` entgegen
und verlangt den internen Header `X-Browser-Capture: receiver-v1`, sodass der
Endpunkt nicht direkt von außen aufrufbar ist.

PDFs werden zunächst nativ gelesen. Bei unzureichender Qualität wird MinerU
verwendet; bei einem eindeutig beschädigten Text-Layer werden die Seiten
zuvor gerastert. HTML/SingleFile wird lokal bereinigt und lädt keine externen
Ressourcen nach.

## Matching und Jobs

- `GET /matching/jobs?profile_id={profile_id}&include_archived={bool}`
- `GET /matching/jobs/{job_id}`
- `PATCH /matching/jobs/{job_id}/metadata`
- `POST /matching/jobs/{job_id}/archive`
- `POST /matching/jobs/{job_id}/restore`
- `DELETE /matching/jobs/{job_id}`
- `GET /matching/results?job_id={job_id}&profile_id={profile_id}`
- `GET /matching/target-fit?job_id={job_id}&profile_id={profile_id}`
- `GET /matching/context?job_id={job_id}&profile_id={profile_id}`
- `POST /matching/evaluate`
- `POST /matching/run`

Der Matching-Kontext enthält den normalisierten Jobtext und kanonische
Profilevidenz. Referenzen und Kontaktdaten werden ausgeschlossen. Archivierte
Jobs werden standardmäßig aus `matching/jobs` ausgeblendet. `target-fit`
liefert den vom Qualifikations-Fit getrennten Abgleich mit dem strukturierten
Zielprofil.

## Profile

- `GET /profiles`
- `POST /profiles`
- `GET /profiles/{profile_id}`
- `PATCH /profiles/{profile_id}`
- `GET /profiles/taxonomy/skills`

Ressourcen unter einem Profil:

- `skills`
- `experiences`
- `education`
- `certificates`
- `references`

Für diese Ressourcen stehen Listen-, Anlege- und Änderungsendpunkte bereit.
Einträge werden über
`DELETE /profiles/{profile_id}/{resource_type}/{item_id}` deaktiviert.
Revisionen liefert
`GET /profiles/{profile_id}/revisions/{entity_type}/{entity_id}`.

## CV-Vorschläge

- `GET /profiles/{profile_id}/cv-imports`
- `POST /profiles/{profile_id}/cv-imports`
- `POST /profiles/{profile_id}/cv-imports/structured`
- `POST /profiles/{profile_id}/cv-imports/pdf`
- `POST /profiles/{profile_id}/portfolio-imports/structured`
- `POST /profiles/{profile_id}/portfolio-imports/source`
- `POST /profiles/{profile_id}/cv-suggestions/{suggestion_id}/apply`
- `POST /profiles/{profile_id}/cv-suggestions/{suggestion_id}/reject`

CV- und Portfolio-Importe verändern das kanonische Profil nicht automatisch.
Vorschläge müssen geprüft, übernommen oder verworfen werden.
`portfolio-imports/source` akzeptiert den vollständigen Inhalt der
Portfolio-Datei `projects.js`.
