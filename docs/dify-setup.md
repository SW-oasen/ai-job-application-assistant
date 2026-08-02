# Dify lokal betreiben

## Start

Im Docker-Verzeichnis der lokalen Dify-Installation:

```powershell
docker compose up -d
```

Weboberfläche: `http://localhost:8088/`

## Administratorzugang zurücksetzen

```powershell
docker compose exec api flask reset-email
docker compose exec api flask reset-password
```

Zugangsdaten werden ausschließlich außerhalb des Repositorys
verwaltet. Passwörter und Administrator-E-Mail-Adressen nicht in dieser Datei
ablegen.


## Ollama aus Dify erreichen

Standardadresse vom Container zum Host:

```text
http://host.docker.internal:11434
```

Workflow-Import und API-Schlüssel sind in
[workflow/dify/README.md](../workflow/dify/README.md) beschrieben.

Nach dem Import der optionalen Review-Workflows muss das Backend die
Migration für die Review-Historie erhalten:

```powershell
docker compose exec application-assistant-backend alembic upgrade head
```

Hinweis zur Konfiguration von Review-Workflows

Die Anwendung erwartet keine `workflow_id` mehr in den Review-Payloads.
Stattdessen wird die Auswahl über den Dify-App-API-Key gesteuert, der in
der Umgebungsvariable `REVIEW_WORKFLOWS` hinterlegt werden kann (JSON).
Beispiel (vereinfachte Form):

```text
REVIEW_WORKFLOWS='{"app-abc123": {"enabled": true, "api_key": "app-abc123"}}'
```

Wichtig: Die importierten Workflows erwarten das Formularfeld `attempt`
als Text/String (nicht numerisch). Fehler oder fehlende API-Keys führen
zu protokollierten Review-Fehlern, blockieren jedoch nicht den Importvorgang.
