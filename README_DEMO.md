# Application Assistant – Demo-Umgebung

Diese Anleitung beschreibt die isolierte Demo für Präsentationen. Sie läuft
unter `http://localhost:8081` und verwendet eine eigene Datenbank, eigene
Dokumente und eine eigene ChromaDB. Die reguläre Anwendung auf Port `8080`
wird nicht gelesen oder verändert.

## Voraussetzungen

- Docker Desktop läuft.
- Das gemeinsame Docker-Netzwerk für Dify, PostgreSQL und MinerU existiert
  (standardmäßig `docker_default`).
- PostgreSQL ist erreichbar.
- Die reguläre `.env` enthält – falls in der Präsentation verwendet – die
  Zugangsdaten für Dify und MinerU.

## Einmalige Konfiguration

1. Eine separate, leere PostgreSQL-Datenbank anlegen:

   ```powershell
   docker exec -it docker-db_postgres-1 psql -U postgres -c "CREATE DATABASE application_assistant_demo;"
   ```

   Falls der PostgreSQL-Container anders heißt, den Namen entsprechend
   ersetzen.

2. Demo-Konfiguration erzeugen:

   ```powershell
   Copy-Item .env.demo.example .env.demo
   ```

3. In `.env.demo` die funktionierende `DATABASE_URL` aus der regulären
   `.env` übernehmen und nur den Datenbanknamen am Ende ersetzen:

   ```env
   DATABASE_URL=postgresql+psycopg://postgres:<passwort>@docker-db_postgres-1:5432/application_assistant_demo
   DEMO_DATABASE_NAME=application_assistant_demo
   ```

   Die Datenbank muss exakt `application_assistant_demo` heißen. Der
   Demo-Container verweigert andernfalls den Start und schützt so vor einer
   versehentlichen Verbindung mit der regulären Datenbank.

4. Den Demo-Workflow `workflow/dify/matching-demo-v4.yml` in Dify
   importieren und veröffentlichen. Dify muss den zusätzlichen internen
   Dienstnamen erlauben:

   ```env
   SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=application-assistant-backend,application-assistant-demo
   ```

   Nach dem Veröffentlichen den API-Schlüssel dieses Workflows als
   `DIFY_MATCHING_WORKFLOW_API_KEY` in `.env.demo` eintragen. Für eine
   vollständig getrennte Präsentation empfiehlt sich eine eigene, in Dify
   veröffentlichte Demo-Kopie des Workflows.

## Demo starten und Beispieldaten erzeugen

```powershell
docker compose -f compose.demo.yaml up -d --build application-assistant-demo chromadb-demo
docker compose -f compose.demo.yaml --profile tools run --rm demo-seed
```

Danach öffnen:

```text
http://localhost:8081/
```

Das Seed-Skript legt das Profil **Demo Testerprofil**, passende Beispiel-Skills
und sechs fiktive Stellenanzeigen von Pseudofirmen an. Es kann gefahrlos erneut
ausgeführt werden: Bereits angelegte Demo-Jobs werden nicht dupliziert, echte
während einer Demo importierte Jobs werden nicht überschrieben.

## Ablauf während der Präsentation

1. Sicherstellen, dass die Browser-Adresse mit `http://localhost:8081`
   beginnt.
2. Unter **Verwaltung > Profil** `Demo Testerprofil` auswählen und
   **Profil laden** klicken.
3. Prüfen, ob der Profil-Chip im Kopfbereich `Demo Testerprofil` zeigt.
4. Die sechs fiktiven Stellen für die Übersicht, Statusverwaltung und
   Detailseiten verwenden.
5. Für eine Live-Demonstration kann eine echte, bewusst ausgewählte
   Stellenanzeige importiert, extrahiert und gematcht werden. Sie wird nur in
   `application_assistant_demo` gespeichert.

Hinweis: Dify und MinerU erhalten beim Live-Import den Inhalt der ausgewählten
Anzeige zur Verarbeitung. Echte Jobs, Bewerbungen und Profildaten der
regulären Datenbank werden dabei nicht übermittelt oder verändert.

## Eigenes Testerprofil verwenden

Das Seed-Profil ist neutral. Falls ein bereits angelegtes Testerprofil benötigt
wird, dieses in der regulären Anwendung unter **Verwaltung > Profil**
exportieren und anschließend ausschließlich in der Demo importieren.
Profil-Exporte enthalten keine Stellenanzeigen.

## Code-Stand aktualisieren

Demo und Produktion nutzen denselben Quellcode, aber getrennte Container. Nach
UI- oder Backend-Änderungen den Demo-Container neu bauen:

```powershell
docker compose -f compose.demo.yaml up -d --build --force-recreate application-assistant-demo
```

Anschließend die Demo-Seite mit `Strg` + `F5` hart neu laden.

Für die reguläre Anwendung auf Port `8080` ist ein eigener Neubau nötig:

```powershell
docker compose up -d --build --force-recreate application-assistant-backend
```

## Nützliche Befehle

```powershell
# Status der Demo-Container
docker compose -f compose.demo.yaml ps

# Demo-Backend stoppen; Daten bleiben erhalten
docker compose -f compose.demo.yaml stop

# Demo wieder starten
docker compose -f compose.demo.yaml start

# Seed-Daten erneut prüfen bzw. fehlende Daten ergänzen
docker compose -f compose.demo.yaml --profile tools run --rm demo-seed
```

Die reguläre Anwendung und die Demo dürfen parallel laufen: Produktion auf
Port `8080`, Demo auf Port `8081`.
