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
