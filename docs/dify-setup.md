# Dify lokal betreiben

## Start

Im Docker-Verzeichnis der lokalen Dify-Installation:

```powershell
docker compose up -d
```

Weboberfläche: `http://localhost:8088/`

## Öffentliche und interne URLs konfigurieren

Leere URL-Variablen führen im Dify-Webcontainer zu einem Fallback auf
`http://localhost`. Das ist innerhalb des Containers nicht die Dify-API und
zeigt sich in der GUI als unerwarteter Rendering-Fehler sowie als
`ECONNREFUSED` im `web`-Log. In
`D:\Projects\AI\Dify\dify-main\docker\.env` müssen für die lokale
Installation daher diese Werte gesetzt sein:

```env
CONSOLE_API_URL=http://localhost:8088
CONSOLE_WEB_URL=http://localhost:8088
APP_API_URL=http://localhost:8088
APP_WEB_URL=http://localhost:8088
NEXT_PUBLIC_SOCKET_URL=ws://localhost:8088
SERVER_CONSOLE_API_URL=http://api:5001
```

Die ersten fünf Werte sind die vom Browser erreichbare Adresse. Der letzte
Wert bleibt die interne Docker-Adresse und darf nicht auf `localhost` zeigen.
Nach einer Änderung Web, API und Nginx neu erstellen:

```powershell
cd D:\Projects\AI\Dify\dify-main\docker
docker compose up -d --force-recreate web nginx
```

## Dify-Nginx nach Docker-Neustarts stabil halten

Docker vergibt Containern nach einem Neustart gegebenenfalls neue interne
IP-Adressen. Dify-Nginx darf die API deshalb nicht nur beim eigenen Start
auflösen. Die Dify-Nginx-Vorlage muss stattdessen den Docker-DNS-Resolver zur
Laufzeit verwenden.

In `nginx/conf.d/default.conf.template` innerhalb von `server { ... }`
ergänzen:

```nginx
resolver 127.0.0.11 valid=30s ipv6=off;
set $api_upstream api:5001;
```

Danach jede Weiterleitung zur Dify-API von:

```nginx
proxy_pass http://api:5001;
```

zu folgender Variante ändern:

```nginx
proxy_pass http://$api_upstream;
```

Betroffen sind mindestens die Locations `/console/api`, `/api`, `/v1`,
`/openapi`, `/files`, `/mcp` und `/triggers`. `127.0.0.11` ist dabei der
interne DNS-Dienst von Docker, nicht die Windows-Loopback-Adresse.

Nach der Änderung Nginx aus dem Dify-Compose-Projekt neu erstellen. Im
Application-Assistant-Workspace gibt es keinen Dienst `nginx`.

```powershell
docker compose -f D:\Projects\AI\Dify\dify-main\docker\docker-compose.yaml up -d --force-recreate nginx
```

Alternativ zuerst in das Dify-Docker-Verzeichnis wechseln und dann den
Compose-Befehl ohne `-f` ausführen:

```powershell
cd D:\Projects\AI\Dify\dify-main\docker
docker compose up -d --force-recreate nginx
```

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
# CV-Recommender

Importiere `workflow/dify/03-cv-recommender-v1.yml` als Workflow und veröffentliche ihn. Hinterlege den API-Key anschließend ausschließlich in `.env` als `DIFY_CV_RECOMMENDER_WORKFLOW_API_KEY`. Der Workflow erhält das Master-Profil und eine Auswahl-Inventarliste vom Backend; er muss die IDs aus dieser Liste unverändert zurückgeben. Ohne konfigurierten Key ist die Aktion „CV-Empfehlung erstellen“ absichtlich nicht verfügbar.
