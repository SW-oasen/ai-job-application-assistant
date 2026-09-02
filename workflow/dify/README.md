# Dify-Workflows

Dieses Verzeichnis enthält ausschließlich die importierbaren und
versionierten Workflow-DSLs des Application Assistant.

| Datei | Zweck |
|---|---|
| `00-import_cv_pdf.yml` | CV-PDF extrahieren und prüfbare Profilvorschläge speichern |
| `01-import-job-url-v3.yml` | öffentliche Stellen-URL importieren und validieren |
| `02-matching-v4.yml` | Jobanforderungen aus dem gespeicherten Job übernehmen oder extrahieren und evidenzbasiert bewerten |
| `03-job-metadata-fallback-v1.yml` | fehlende oder unplausible Metadaten ergänzen |
| `06-job-extraction-v1.yml` | vollständige Job-Extraktion für Metadaten, Tätigkeiten und Anforderungen |
| `04-job-extraction-review-v1.yml` | strukturierte Job-Extraktionen gegen den Stellentext prüfen |
| `05-job-matching-review-v1.yml` | gespeicherte Job-Matchings auf Evidenz und Konsistenz prüfen |

Lokale Sicherungen älterer Workflows unter `workflow/backup` sind ignoriert
und nicht Bestandteil des öffentlichen Repositorys.

## Gemeinsame Voraussetzungen

- Application Assistant und Dify laufen im gemeinsamen Docker-Netzwerk.
- Das Backend ist aus Dify unter
  `http://application-assistant-backend:8080` erreichbar.
- Ollama-Provider und das in der DSL konfigurierte Modell sind in Dify
  verfügbar.
- Neue DSLs werden als neue Dify-Apps importiert und ersetzen vorhandene Apps
  nicht automatisch.

Für HTTP-Nodes zum Backend muss der Dify-SSRF-Proxy gezielt den internen
Servicenamen erlauben:

```env
SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=application-assistant-backend,application-assistant-demo
```

## Import und Veröffentlichung

Für jeden benötigten Workflow:

1. DSL in Dify importieren.
2. Modell- und HTTP-Konfiguration kontrollieren.
3. Workflow mit Testdaten ausführen.
4. Workflow veröffentlichen.
5. Auf der API-Zugangsseite einen eigenen Schlüssel erzeugen.
6. Schlüssel ausschließlich in der lokalen Backend-`.env` hinterlegen.

API-Schlüssel gehören nicht in DSLs, Browser-Code oder Git.

## CV-Import

`00-import_cv_pdf.yml` erwartet:

- `profile_id`: UUID des Zielprofils
- `source_language`: `de` oder `en`
- `source_filename`: optionaler Anzeigename
- `local_cv_pdf`: eine PDF-Datei

Der Workflow extrahiert strukturierte Daten und übergibt sie an:

```text
POST /profiles/{profile_id}/cv-imports/structured
```

Das Backend legt ausschließlich prüfbare Vorschläge an. Eine automatische
Übernahme in das kanonische Profil findet nicht statt. Für den direkten Start
aus der Profilverwaltung wird der veröffentlichte Workflow-Schlüssel als
`DIFY_CV_WORKFLOW_API_KEY` gespeichert.

## Jobimport per URL

`01-import-job-url-v3.yml` erwartet eine öffentliche HTTP(S)-URL. Der
Backend-Import blockiert lokale und private Ziele, validiert Redirects und
speichert nur ausreichend verwertbare Inhalte.

Ein erfolgreicher Lauf liefert eine `job_id`. Erwartbare Quellsperren wie
HTTP 403 oder 429 werden als kontrolliertes Ergebnis zurückgegeben und lösen
kein Matching aus.

## Matching

`02-matching-v4.yml` ist der produktive Workflow und erwartet:

- `job_id`
- `profile_id`

Für die isolierte Demo `matching-demo-v4.yml` importieren und veröffentlichen.
Diese Variante verwendet ausschließlich
`http://application-assistant-demo:8080`.

Der Workflow lädt den gespeicherten Job aus dem Backend. Wenn dort bereits
strukturierte Anforderungen vorliegen, werden sie bevorzugt verwendet;
andernfalls extrahiert der Workflow sie aus dem Jobtext und übergibt sie an
`/matching/evaluate`. Das Backend erzeugt Evidenz aus kanonischen Skills,
Berufserfahrung, Ausbildung und Zertifikaten.

Referenzen und Kontaktdaten werden nicht als Matching-Evidenz ausgegeben.
Berufliche, schulische, projektbezogene und Trainingskontexte bleiben
unterscheidbar. Für den Start aus der Matching-Oberfläche wird der Schlüssel
als `DIFY_MATCHING_WORKFLOW_API_KEY` gespeichert.

## Metadaten-Fallback

`03-job-metadata-fallback-v1.yml` ergänzt fehlende oder unplausible
Job-Metadaten nach dem deterministischen Regelparser. Automatisch übernommen
werden nur bisher leere Werte mit mindestens `0,85` Konfidenz und einer
prüfbaren Fundstelle im Ausgangstext.

Der Schlüssel wird als `DIFY_METADATA_WORKFLOW_API_KEY` gespeichert. Ist der
Workflow nicht verfügbar, bleibt der normale Import funktionsfähig.

## Reviews

`04-job-extraction-review-v1.yml` und `05-job-matching-review-v1.yml`
erwarten die generischen Eingaben `review_type`, `source_data_json`,
`generated_result_json`, `context_json`, `retry_instructions_json` und
`attempt`. Beide geben `review_json` aus, das dem Backend-Schema
`ReviewResult` entspricht.

Reviews sind standardmäßig deaktiviert. Nach Import, Veröffentlichung und
Erzeugung je eines API-Schlüssels werden sie in der Backend-`.env` als ein
JSON-Wert aktiviert. Der API-Schlüssel einer veröffentlichten Dify-App wählt
die auszuführende App aus:

```env
REVIEW_WORKFLOWS={"job_extraction":{"api_key":"<secret>","workflow_version":"v1","prompt_version":"v1"},"job_matching":{"api_key":"<secret>","workflow_version":"v1","prompt_version":"v1"}}
```

Ohne einen vollständigen Eintrag mit API-Schlüssel bleibt der jeweilige
Produktionspfad unverändert. Extraktionsreviews werden direkt nach URL-,
HTML-, PDF- und Reimport ausgeführt. Matching-Reviews werden nach einem
erfolgreichen Matching gespeichert; sie ändern das angezeigte Matching noch
nicht automatisch.

Vor der Aktivierung muss die Review-Historie migriert werden:

```powershell
docker compose exec application-assistant-backend alembic upgrade head
```

Der Prüflauf ist im Job-Detail unter „Prüfverlauf“ über
`GET /matching/jobs/{job_id}/reviews` einsehbar.

## Lokale Workflow-Sicherungen

`workflow/backup` kann lokal für unveröffentlichte oder historische Exporte
verwendet werden. Der Pfad ist ignoriert. Inhalte daraus dürfen nicht in der
öffentlichen Dokumentation vorausgesetzt werden.
