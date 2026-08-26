# Entwicklungsumgebung und Tests

Dieses Dokument beschreibt die lokale Umgebung für Entwicklung und Tests des
AI Application Assistant. Es dient als Referenz, wenn Python oder Docker nicht
aus der erwarteten Umgebung gestartet werden.

## Python-Umgebung

Die Abhängigkeiten liegen in `backend/.venv` (nicht in der globalen
Python-Installation). Befehle daher aus dem Verzeichnis `backend` ausführen.

### PowerShell

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

Alternativ ohne Aktivierung:

```powershell
backend\.venv\Scripts\python.exe -m pytest -q
```

### Git Bash

```bash
cd backend
source .venv/Scripts/activate
python -m pytest -q
```

Alternativ ohne Aktivierung:

```bash
backend/.venv/Scripts/python.exe -m pytest -q
```

Eine installierte Bibliothek kann so geprüft werden:

```bash
python -m pip show fastapi
```

Wenn `fastapi` fehlt, wurde wahrscheinlich der globale Python-Interpreter
verwendet. Dann den Befehl mit `backend/.venv/Scripts/python.exe` wiederholen.

## Konfiguration

Die lokale Konfiguration liegt in `.env` im Workspace-Root. Sie enthält unter
anderem die Datenbankverbindung und API-Schlüssel und darf nicht in Git
committet werden. Als Vorlage dient `.env.example`.

Vor Backend- oder Integrationstests müssen die benötigten Docker-Dienste
laufen und die `.env`-Werte verfügbar sein.

## Docker und PostgreSQL

Den laufenden PostgreSQL-Container ermitteln:

```bash
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```

Der Datenbankcontainer heißt in der lokalen Umgebung derzeit
`docker-db_postgres-1`. Tabellen anzeigen:

```bash
docker exec -it docker-db_postgres-1 psql -U postgres -d application_assistant -c '\dt'
```

Die relationale Datenbank liegt in einem Docker-Volume und nicht im
Workspace. Vor potenziell datenverändernden Tests einen Dump erstellen, zum
Beispiel im Verzeichnis `backup`:

```bash
docker exec -i docker-db_postgres-1 pg_dump -U postgres -d application_assistant -Fc > database-backup.dump
```

Auch `application-documents` und `chroma-data` sind separate Docker-Volumes.
Sie werden von einem 7z-Archiv des Workspace nicht erfasst.

## Tests unter Windows

Die Python-Syntax kann unabhängig von externen Diensten geprüft werden:

```bash
python -m compileall -q app
```

Einige Integrationstests benötigen PostgreSQL, Dify oder weitere Dienste. Wenn
unter Windows ein Fehler wie
`Psycopg cannot use the ProactorEventLoop` erscheint, ist der Testlauf an der
Windows-Eventloop-Kompatibilität oder an der externen Dienstkonfiguration
gescheitert, nicht an einer fehlenden FastAPI-Installation.

## Sicherheits- und Sicherungshinweise

- `.env`, Datenbank-Dumps und exportierte Profile enthalten persönliche Daten
  beziehungsweise Zugangsschlüssel.
- Backups verschlüsseln und außerhalb des Git-Repositories aufbewahren.
- Vor Profilimporten zuerst einen PostgreSQL-Dump erstellen.
