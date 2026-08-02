# Betrieb und Readiness

Ein offener Port oder ein einzelner HTTP-Status beweist noch nicht, dass Dify
vollständig gestartet ist. Insbesondere die Weboberfläche kann bereits
antworten, während API, Datenbankmigrationen oder JavaScript-Ressourcen noch
nicht verwendbar sind.

## Lokaler Schnelltest

Aus dem Workspace:

```powershell
.\scripts\check-local-readiness.ps1
```

Der Test wartet standardmäßig bis zu 120 Sekunden und prüft:

1. `http://localhost:8080/health` liefert die erwartete Backend-Antwort.
2. `http://localhost:8088/signin` liefert nicht nur HTTP 200, sondern eine
   plausible, vollständig ausgelieferte Dify-Anmeldeseite.

Andere Adressen oder eine längere Startfrist können übergeben werden:

```powershell
.\scripts\check-local-readiness.ps1 `
  -BackendUrl http://localhost:8080 `
  -DifyUrl http://localhost:8088 `
  -TimeoutSeconds 240
```

Der Test führt keine Anmeldung durch und benötigt keine Zugangsdaten.

## Vor einem Deployment

Zusätzlich zum Schnelltest werden folgende Fälle geprüft:

- Start aus vollständig gestopptem Zustand;
- verzögerter Start von PostgreSQL und Redis;
- Neustart nur von Dify API, Worker, Web und Nginx;
- Erreichbarkeit der internen Backend-Adresse
  `http://application-assistant-backend:8080/health` aus dem Dify-Netz;
- erfolgreicher automatischer Lauf von `alembic upgrade head`, bevor das
  Application-Assistant-Backend HTTP-Anfragen annimmt;
- Anmeldung in einer neuen privaten Browsersitzung;
- Verhalten einer vorhandenen Browsersitzung mit alten Cookies;
- Laden der Workflow-Seite einschließlich JavaScript- und API-Anfragen;
- verständliche Fehleranzeige, solange ein abhängiger Dienst noch nicht bereit
  ist.

Für den Produktivbetrieb sollen die abhängigen Container echte Healthchecks
besitzen und abhängige Dienste erst nach erfolgreicher Readiness freigegeben
werden. Ein bloßes `depends_on` ohne Health-Bedingung reicht dafür nicht.

### Reviewer / Dify-Workflows und Readiness

Falls die Anwendung auf optionale Dify-Review-Workflows angewiesen ist, gelten
weitere Prüfpunkte für die Readiness:

- Die importierten Dify-Apps sollten erfolgreich geladen und die zugehörigen
  API-Keys (`REVIEW_WORKFLOWS`) in der Backend-Umgebung vorhanden sein.
- Nach dem Import neuer oder geänderter Workflows ist die Datenbankmigration
  für die Review-Historie erforderlich:

```powershell
docker compose exec application-assistant-backend alembic upgrade head
```

- Fehlerhafte oder nicht erreichbare Review-Workflows sollen den Import nicht
  blockieren; das Backend protokolliert Review-Fehler in der Historie und
  liefert weiterhin die Hauptfunktionalität aus.

## Diagnose bei leerer Dify-Seite

1. Den Readiness-Test ausführen und dessen konkreten Fehler festhalten.
2. Dify in einer privaten Browsersitzung öffnen.
3. Falls die private Sitzung funktioniert, Cookies und Site-Daten der lokalen
   Dify-Adresse erneuern.
4. Falls sie ebenfalls fehlschlägt, Containerstatus und Logs von Web, API,
   Worker und Nginx prüfen.

Ein Neustart wird erst nach diesen lesenden Prüfungen vorgenommen. So bleibt
sichtbar, welcher Dienst tatsächlich noch nicht bereit war.
