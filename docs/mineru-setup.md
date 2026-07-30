---

# MinerU lokal mit Docker konfigurieren

## A.1 Zweck

MinerU wird als separater lokaler Dokumentenservice betrieben. Der Application Assistant und Dify greifen per HTTP darauf zu.

MinerU verarbeitet unter anderem PDF- und Bilddateien zu Markdown oder JSON. Der FastAPI-Dienst stellt unter anderem folgende Endpunkte bereit:

- `GET /health`
- `POST /tasks`
- `POST /file_parse`
- `GET /tasks/{task_id}`
- `GET /tasks/{task_id}/result`

Die interaktive API-Dokumentation ist nach erfolgreichem Start unter `http://127.0.0.1:8000/docs` erreichbar.

## A.2 Voraussetzungen

- Windows mit Docker Desktop und WSL2-Unterstützung
- funktionierender NVIDIA-Treiber
- Docker-GPU-Unterstützung
- ausreichend freier Speicherplatz
- Git
- Internetverbindung für Image-Build und Modelldownload

GPU-Test:

```bash
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
```

Eine kompatible CUDA-Image-Version kann je nach System abweichen.

## A.3 Repository klonen

```bash
cd /d/Projects/AI/Dify
git clone https://github.com/opendatalab/MinerU.git
cd MinerU
```

Für reproduzierbare Installationen später besser einen Release-Tag statt dauerhaft `master` verwenden:

```bash
git fetch --tags
git tag --sort=-version:refname | head
git checkout <passender-release-tag>
```

Vor einem Update Änderungen in Release Notes und Docker-Konfiguration prüfen.

## A.4 Docker-Image bauen

Im Repository existieren:

```text
docker/
├── compose.yaml
├── global/
│   └── Dockerfile
└── china/
    └── Dockerfile
```

Außerhalb Chinas den globalen Dockerfile verwenden.

Vom Repository-Root:

```bash
cd /d/Projects/AI/Dify/MinerU
docker build -t mineru:latest -f docker/global/Dockerfile .
```

Wichtig:

- Der abschließende Punkt ist der Build-Kontext.
- Das Image wird lokal als `mineru:latest` angelegt.
- Ein Docker-Login ist dafür nicht erforderlich.
- Der Build ist sehr groß, weil unter anderem Python-, CUDA-, PyTorch-, OCR-, Layout- und VLM-Abhängigkeiten enthalten sein können.
- Build und erster Start können lange dauern.

Image prüfen:

```bash
docker images mineru
```

Erwartung:

```text
REPOSITORY   TAG       IMAGE ID       CREATED
mineru       latest    ...
```

## A.5 Warum `docker compose up -d` allein nicht funktioniert

Die Services in `docker/compose.yaml` verwenden Compose-Profile:

```text
api
gradio
openai-server
router
```

Ohne Profil wird kein Service ausgewählt:

```text
no service selected
```

Profile anzeigen:

```bash
cd /d/Projects/AI/Dify/MinerU/docker
docker compose config --profiles
```

## A.6 MinerU API starten

Für Dify und das Python-Backend wird zunächst nur das Profil `api` benötigt:

```bash
cd /d/Projects/AI/Dify/MinerU/docker
docker compose --profile api up -d
```

Status prüfen:

```bash
docker compose --profile api ps
```

Logs anzeigen:

```bash
docker logs -f mineru-api
```

Der Container verwendet laut Compose-Konfiguration:

```text
Container: mineru-api
Host-Port: 8000
Container-Port: 8000
Restart: always
GPU: device 0
```

## A.7 API testen

Im Browser:

```text
http://127.0.0.1:8000/docs
```

Healthcheck in Git Bash:

```bash
curl.exe http://127.0.0.1:8000/health
```

Alternativ:

```bash
docker exec mineru-api curl -f http://localhost:8000/health
```

Ein erfolgreicher Healthcheck muss HTTP 200 liefern.

## A.8 Beispiel für einen PDF-Test

Synchroner Test in Git Bash:

```bash
curl -X POST "http://127.0.0.1:8000/file_parse" \
  -F "files=@/d/Pfad/zur/stellenanzeige.pdf" \
  -F "return_md=true"
```

Asynchroner Test:

```bash
curl -X POST "http://127.0.0.1:8000/tasks" \
  -F "files=@/d/Pfad/zur/stellenanzeige.pdf" \
  -F "return_md=true"
```

Anschließend:

```bash
curl http://127.0.0.1:8000/tasks/<task_id>
curl http://127.0.0.1:8000/tasks/<task_id>/result
```

Für kurze Stellenanzeigen ist der synchrone Endpunkt zunächst einfacher. Bei längeren Dokumenten sollte später der asynchrone Ablauf verwendet werden.

## A.9 Dify mit MinerU verbinden

Da Dify in Docker läuft, darf innerhalb des Dify-Containers nicht `localhost:8000` verwendet werden. `localhost` würde dort auf den Dify-Container selbst zeigen.

Unter Docker Desktop für Windows zunächst verwenden:

```text
http://host.docker.internal:8000
```

Dify-MinerU-Plugin:

```text
Server type: Local Deployment
Base URL: http://host.docker.internal:8000
API key/token: leer, sofern die lokale Installation keinen Token verlangt
```

Vor der Plugin-Konfiguration aus einem Docker-Container testen:

```bash
docker run --rm curlimages/curl \
  http://host.docker.internal:8000/health
```

Wenn das funktioniert, sollte auch Dify den Dienst erreichen können.

## A.10 Verbindung über gemeinsames Docker-Netzwerk

Langfristig ist ein gemeinsames Docker-Netzwerk stabiler als der Host-Zugriff.

Beispiel:

```bash
docker network create ai-services
docker network connect ai-services mineru-api
```

Der passende Dify-Container muss ebenfalls mit diesem Netzwerk verbunden werden.

Dann kann intern verwendet werden:

```text
http://mineru-api:8000
```

Dies erst umsetzen, wenn die vorhandene Dify-Compose-Struktur geprüft wurde. Keine Netzwerknamen oder Container ohne Prüfung fest codieren.

## A.11 Automatischer Neustart

Die Compose-Datei enthält:

```yaml
restart: always
```

Nach erfolgreicher Erstellung startet der Container normalerweise beim Start von Docker Desktop erneut.

Nicht bei jedem Start erforderlich:

```bash
docker build ...
```

Das Image muss nur neu gebaut werden, wenn:

- MinerU aktualisiert wird,
- ein anderer Release ausgecheckt wird,
- der Dockerfile geändert wird,
- Abhängigkeiten aktualisiert werden sollen,
- das lokale Image gelöscht wurde.

Manueller Start:

```bash
docker start mineru-api
```

Manuelles Stoppen:

```bash
docker stop mineru-api
```

Oder über Compose:

```bash
docker compose --profile api stop
docker compose --profile api start
```

Container entfernen:

```bash
docker compose --profile api down
```

Das lokale Image bleibt dabei normalerweise erhalten.

## A.12 Optional: Gradio-Weboberfläche

Zum manuellen Testen kann zusätzlich das Gradio-Profil gestartet werden:

```bash
docker compose --profile gradio up -d
```

Aufruf:

```text
http://127.0.0.1:7860
```

Für den regulären Application-Assistant-Betrieb ist Gradio nicht erforderlich.

## A.13 Nicht benötigte Profile

### `openai-server`

Port `30000`. Für OpenAI-kompatible VLM-/HTTP-Client-Szenarien. Für den ersten Dify-PDF-Import nicht nötig.

### `router`

Port `8002`. Für mehrere MinerU-Dienste beziehungsweise Multi-GPU-Orchestrierung. Für die lokale Einzel-GPU-Installation zunächst nicht nötig.

### `gradio`

Nur Weboberfläche zum manuellen Testen.

Empfohlener Start:

```bash
docker compose --profile api up -d
```

## A.14 GPU-Speicherprobleme

Die Compose-Datei enthält kommentierte Optionen wie:

```yaml
# --gpu-memory-utilization 0.5
```

Diese Option nicht vorsorglich aktivieren. Erst bei konkreten VRAM-Fehlern verwenden und die aktuelle MinerU-Dokumentation prüfen.

Da auf dem AI-PC auch Ollama beziehungsweise lokale LLMs laufen, können GPU-Konflikte auftreten.

Praktische Strategie:

1. große Ollama-Modelle vor MinerU-Verarbeitung entladen,
2. MinerU einzeln testen,
3. GPU-Auslastung mit `nvidia-smi` beobachten,
4. erst danach Parallelbetrieb testen.

## A.15 Häufige Fehler

### Fehler: `no service selected`

Ursache: Kein Compose-Profil ausgewählt.

Lösung:

```bash
docker compose --profile api up -d
```

### Fehler: `pull access denied for mineru`

Ursache: `mineru:latest` existiert lokal noch nicht. Compose versucht vergeblich, es aus einer Registry zu laden.

Lösung:

```bash
cd /d/Projects/AI/Dify/MinerU
docker build -t mineru:latest -f docker/global/Dockerfile .
```

Kein Docker-Login erforderlich.

### Fehler: Dify meldet ungültige Base URL

Prüfen:

```bash
curl.exe http://127.0.0.1:8000/health
docker run --rm curlimages/curl http://host.docker.internal:8000/health
```

Dify-URL:

```text
http://host.docker.internal:8000
```

### Fehler: Container startet und beendet sich wieder

Prüfen:

```bash
docker ps -a
docker logs --tail=200 mineru-api
```

Typische Ursachen:

- fehlende GPU-Unterstützung,
- inkompatibler Treiber,
- zu wenig VRAM,
- unvollständiger Modelldownload,
- zu wenig Arbeitsspeicher,
- zu wenig freier Speicherplatz.

### Fehler: Healthcheck bleibt lange auf `starting`

Der erste Start kann Modelle initialisieren. Logs beobachten:

```bash
docker logs -f mineru-api
```

Bei echten Fehlern nicht wiederholt Container neu erstellen, bevor die Logmeldung analysiert wurde.

## A.16 Update-Vorgehen

Vor Update:

```bash
cd /d/Projects/AI/Dify/MinerU
git status
git describe --tags --always
docker images mineru
```

Aktualisieren:

```bash
git fetch --tags
git checkout <neuer-getesteter-release-tag>
docker build -t mineru:<version> -f docker/global/Dockerfile .
```

Für mehr Reproduzierbarkeit später die Compose-Datei auf einen versionierten Image-Tag anpassen:

```yaml
image: mineru:<version>
```

Nicht ungeprüft alte Container und Images löschen. Zuerst die neue Version testen.

---

# Anhang B – Konfigurationsvariablen des Application Assistant

Beispiel `.env.example`:

```env
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8080
LOG_LEVEL=INFO

DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/application_assistant

MINERU_BASE_URL=http://host.docker.internal:8000
MINERU_TIMEOUT_SECONDS=300

URL_IMPORT_TIMEOUT_SECONDS=30
URL_IMPORT_MAX_BYTES=10000000
URL_IMPORT_MIN_TEXT_LENGTH=500

PLAYWRIGHT_ENABLED=true
PLAYWRIGHT_TIMEOUT_SECONDS=45

STORE_RAW_HTML=true
STORE_ORIGINAL_FILES=true
```

Zugangsdaten nicht in Git speichern.

---

# Anhang C – Technische Quellen

Bei MinerU ändern sich CLI, Dockerfiles und API-Versionen relativ schnell. Vor späteren Neuinstallationen oder Updates immer die zum ausgecheckten Release passende Dokumentation prüfen.

- MinerU Repository: https://github.com/opendatalab/MinerU
- MinerU Quick Usage: https://opendatalab.github.io/MinerU/usage/quick_usage/
- MinerU Docker Compose: https://github.com/opendatalab/MinerU/blob/master/docker/compose.yaml
- MinerU Ecosystem: https://github.com/opendatalab/MinerU-Ecosystem

---

## 11. Definition of Done für die nächste Hauptetappe

Die nächste Hauptetappe gilt als abgeschlossen, wenn:

- eine Stellen-URL in Dify eingegeben werden kann,
- Dify das eigene FastAPI-Backend aufruft,
- statische und JavaScript-lastige Seiten verarbeitet werden,
- das Backend bereinigtes Markdown zurückgibt,
- das LLM daraus valides Stellen-JSON erzeugt,
- textuelle PDFs normal verarbeitet werden,
- bildbasierte PDFs automatisch über MinerU laufen,
- Importquelle und Rohdaten gespeichert werden,
- mindestens fünf reale Anzeigen erfolgreich getestet wurden,
- Fehler klar angezeigt und protokolliert werden,
- Kernfunktionen automatisierte Tests besitzen.
