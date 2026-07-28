# Dify 

## Konfiguration - Start 

cd /d/Projects/AI/Dify/dify-main/docker
docker-compose up -d

Starten Web GUI
http://localhost:8088/

### Reset Admin Logging

docker compose exec api flask reset-email

docker compose exec api flask reset-password

Aktuelle Zugangsdaten werden ausschließlich außerhalb des Repositorys
verwaltet. Passwörter und Administrator-E-Mail-Adressen nicht in dieser Datei
ablegen.


## Lokale LLMs über Ollama hinzufügen

http://host.docker.internal:11434



