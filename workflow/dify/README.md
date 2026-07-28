# Dify-Workflows

In diesem Verzeichnis werden die vom Application-Assistant-Projekt
bereitgestellten, importierbaren Dify-DSL-Dateien abgelegt.

Die vorhandenen Dateien unter `../backup` sind unveränderte Sicherungen und
werden nicht überschrieben.

## Geplante Übergabereihenfolge

1. `01-import-job-url-v3.yml`
2. vorhandener atomarer Workflow `import CV`
3. `03-matching-v3.yml`

`02b-store-cv-profile-proposals-v2.yml` und
`04-create-cv-and-application-v1.yml` liegen nur noch unter `workflow/backup`.
Sie gehören nicht zum aktuellen MVP.

Vorhandene, bereits funktionierende Workflows werden zuerst auf ihre Ein- und
Ausgabeparameter geprüft. Neue Fassungen erhalten zunächst einen neuen Namen
beziehungsweise eine neue Version und ersetzen keine aktive Dify-App
automatisch.

Der Backend-Health-Endpunkt ist aus Dify im gemeinsamen Docker-Netzwerk unter
`http://application-assistant-backend:8080/health` erreichbar.

## Import Job URL v2

`01-import-job-url-v3.yml` ist eine neue App und überschreibt weder den
vorhandenen Workflow `import job` noch die bereits veröffentlichte v2. Nach dem
Import:

1. prüfen, ob der Ollama-Provider und `qwen3:8b` verfügbar sind,
2. den Backend-Healthcheck testen,
3. eine öffentliche Stellen-URL ausführen,
4. erst nach erfolgreichem Test veröffentlichen.

Der Workflow verwendet keine Backend-IP, sondern den stabilen Docker-DNS-Namen
`application-assistant-backend`.

Der erfolgreiche Workflow gibt `job_id` als eigene Zeichenkette aus. Diese ID
wird vom Backend beim Speichern des validierten Imports erzeugt und später
direkt an `matching v2` übergeben. Ein qualitativ unzureichender Import wird
nicht als gültiger Job gespeichert, erhält keine `job_id` und darf im
Orchestrator kein Matching auslösen.

Dify muss diesen einzelnen internen Domainnamen in seinem SSRF-Proxy erlauben:

```env
SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=application-assistant-backend
```

Die aktuelle v3 behandelt erwartbare Quellsperren wie HTTP 403/429 als
kontrolliertes Ergebnis. Das Backend antwortet dabei mit `success: false`,
ohne einen Job zu speichern. Der Workflow verzweigt in `Import Failed`, ruft
kein LLM auf und liefert `status`, `error_code`, `error_message`, `source_url`
und eine leere `job_id` zurück. HTTP-Retries sind für diesen Aufruf deaktiviert.

## CV-Profilvorschläge v2

`02b-store-cv-profile-proposals-v2.yml` ergänzt den bereits funktionierenden
Workflow `import CV`, ohne ihn zu überschreiben. Der Adapter erwartet:

- `profile_id`: UUID aus `http://localhost:8080/profiles/admin`
- `source_filename`: beschreibender Original-Dateiname, kein Dateipfad
- `source_language`: `de` oder `en`
- `structured_cv_json`: vollständige JSON-Ausgabe `structured_cv` aus
  `import CV`

Im späteren Orchestrator wird `structured_cv` aus `import CV` zunächst als
JSON-String serialisiert und an diesen Adapter übergeben. Der Adapter ruft
anschließend über Docker-DNS auf:

```text
POST http://application-assistant-backend:8080/profiles/{profile_id}/cv-imports/structured
```

Er legt ausschließlich Vorschläge zur Prüfung an. Eine automatische Übernahme
ins kanonische Profil findet nicht statt. Als Ausgabe liefert er `import_id`,
`suggestion_count` und `status`.

Zum Einzeltest nach dem Import in Dify kann das `structured_cv`-Ergebnis des
bestehenden Workflows in `structured_cv_json` eingefügt werden. Danach erscheinen
die Vorschläge in der Profilverwaltung unter `CV-Vorschläge`.

## Import CV PDF

`import_cv_pdf.yml` verbindet die PDF-Extraktion kontrolliert mit der
Profilverwaltung. Der Workflow erwartet:

- `profile_id`: UUID des Zielprofils aus der Profilverwaltung,
- `source_language`: `de` oder `en`,
- `source_filename`: optionaler Anzeigename für die Importhistorie; Standard
  `lebenslauf.pdf`,
- `local_cv_pdf`: genau eine lokale PDF-Datei.

Nach der Extraktion ruft der Workflow den Backend-Adapter auf und legt beim
gewählten Profil ausschließlich prüfbare Vorschläge an. `structured_cv`,
`import_id`, `suggestion_count` und `status` werden ausgegeben. Die Vorschläge
erscheinen unter `http://localhost:8080/profiles/admin` im Bereich
`CV-Vorschläge`.

Dify-Startfelder können die Profile der Backend-Datenbank nicht dynamisch als
Dropdown laden. Deshalb wird die Profil-UUID im Workflow zunächst als Text
übergeben. Die spätere Application-Assistant-Oberfläche soll dafür eine echte
Profilauswahl anbieten.

Die Profilverwaltung stellt diese Profilauswahl inzwischen bereit und kann den
veröffentlichten Workflow serverseitig starten. Dafür wird auf der
API-Zugangsseite der Dify-App ein eigener API-Schlüssel erzeugt und
ausschließlich als `DIFY_CV_WORKFLOW_API_KEY` in der lokalen Backend-`.env`
hinterlegt. Der Schlüssel gehört nicht in die DSL, den Browser oder das
Repository.

Bei Monatsangaben normalisiert das Backend einen Beginn auf den ersten und ein
Ende auf den letzten Tag des Monats. Enthält ein Ausbildungseintrag nur ein
Enddatum, bleibt sein Startdatum leer. Alle Werte bleiben vor der Übernahme
editierbar. Profilzusammenfassungen aus angepassten CVs werden weiterhin nicht
als kanonische Profiltexte übernommen.

## Orchestrator und Workflow-Tool-Bindungen

Dify 1.15 speichert einen Aufruf eines anderen Workflows als Tool-Node mit dem
Provider-Typ `workflow`. Die dazugehörige `provider_id` entsteht erst, wenn der
aufgerufene Workflow in der Zielinstanz veröffentlicht und als Workflow-Tool
konfiguriert wurde. Sie ist deshalb nicht portabel und darf in einer
Übergabe-DSL nicht erfunden werden.

Vor dem endgültigen Export von `05-manage-application.yml` gilt daher diese
Reihenfolge:

1. atomare Workflows importieren und einzeln testen,
2. die benötigten atomaren Workflows veröffentlichen,
3. sie in Dify als Workflow-Tools konfigurieren,
4. die Tool-Nodes im neuen Orchestrator über die Dify-Oberfläche auswählen,
5. den verdrahteten Orchestrator exportieren und unter `workflow/dify`
   versionieren.

Dieser Bindeschritt verändert weder die gesicherten Workflows unter
`workflow/backup` noch deren Inhalt. Bis zur echten Bindung wird kein
Orchestrator als vollständig lauffähig ausgeliefert.

## Matching v2

`03-matching-v2.yml` überschreibt den vorhandenen Workflow `matching` nicht.
Der Workflow erwartet die beim Job-Import erzeugte `job_id` sowie zwei
JSON-Listen: strukturierte Requirements und belegte Profilevidenz.

Der Workflow führt selbst kein freies LLM-Matching aus. Er ruft den
evidenzbasierten Backend-Vertrag `/matching/evaluate` auf. Dadurch kann
Projekt- oder Trainingserfahrung nicht versehentlich als Berufserfahrung
ausgegeben werden. HTTP-Wiederholungen sind deaktiviert, damit fachliche
4xx-/5xx-Fehler nicht als unspezifisches „maximum retries“ erscheinen.

## Matching v3

`03-matching-v3.yml` ist der Nachfolger der v2 und überschreibt den vorhandenen
Workflow nicht. Er erwartet nur `job_id` und `profile_id`. Der Workflow lädt
den gespeicherten Jobtext aus dem Backend, extrahiert daraus mit dem lokalen
LLM strukturierte Anforderungen und übergibt diese zusammen mit der Profil-ID
an `/matching/evaluate`.

Das Backend erzeugt die Evidenz ausschließlich aus kanonischen Skills,
Berufserfahrungen, Ausbildungen und Zertifikaten. Referenzen und Kontaktdaten
werden nicht für das Matching an Dify ausgegeben. Die v2 bleibt als technische
Referenz erhalten.

Für den direkten Start aus der Matching-GUI muss `matching v3` veröffentlicht
sein. Auf der API-Zugangsseite der Dify-App wird ein eigener Schlüssel erzeugt
und ausschließlich als `DIFY_MATCHING_WORKFLOW_API_KEY` in der Backend-`.env`
gespeichert. Eine Konfiguration als „Workflow as Tool“ ist dafür nicht nötig.

## Semantischer Job-Metadaten-Fallback v1

`03-job-metadata-fallback-v1.yml` ergänzt fehlende Pflichtmetadaten nach dem
deterministischen Regelparser. Bis zu 15.000 Zeichen des bereits extrahierten
Anzeigentexts werden vollständig übergeben. Automatisch übernommen werden nur
bisher leere Werte mit mindestens 0,85 Konfidenz und konkreter Fundstelle.

Nach Import und Veröffentlichung der Dify-App wird ihr API-Schlüssel als
`DIFY_METADATA_WORKFLOW_API_KEY` in der Backend-`.env` hinterlegt. Ist der
Workflow nicht konfiguriert oder nicht erreichbar, bleibt der normale Import
funktionsfähig und speichert einen entsprechenden Importhinweis.

## Bewerbungsdokumente v1

`04-create-cv-and-application-v1.yml` erwartet `job_id`, `profile_id` und die
Zielsprache `de` oder `en`. Für dieses Job-Profil-Paar muss zuvor Matching v3
erfolgreich gelaufen sein.

Der Workflow erzeugt zunächst:

- eine zielgerichtete Profilzusammenfassung,
- belegte CV-Anpassungsvorschläge,
- einen Anschreibenentwurf.

Alle drei Ergebnisse werden im Backend getrennt und automatisch versioniert.
Ein erneuter Lauf überschreibt keine bestehende Fassung. Der LLM-Kontext
enthält keine Kontaktdaten und keine Referenzen. Portfolio-Projekte werden in
v1 nur dann erwähnt, wenn später verifizierte Portfolio-Evidenz über den
geplanten Read-only-Connector bereitgestellt wird; der Workflow erfindet keine
Projektangaben.
