# Hybrid Search mit ChromaDB

Die Anwendung speichert relationale Profildaten und Matching-Ergebnisse weiterhin in PostgreSQL. Vektor-Embeddings der Profilevidence werden getrennt in ChromaDB gespeichert. Dadurch muss die bestehende Dify-PostgreSQL-Datenbank nicht durch eine pgvector-fähige Variante ersetzt werden.

## Betrieb

`docker compose up -d --build` startet zusätzlich den Dienst `chromadb`. Die Daten liegen im Volume `chroma-data`.

Die relevanten Einstellungen sind:

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL=bge-m3:latest
EMBEDDING_DIMENSION=1024
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_COLLECTION=profile-evidence
```

`CHROMA_COLLECTION` bezeichnet die persistente Collection, in der die
Profil-Evidence-Embeddings gespeichert werden. Der Name gehört zur gewählten
Embedding-Konfiguration. Bei einem Wechsel von Modell oder Dimension sollte
eine neue Collection verwendet werden, zum Beispiel:

```env
CHROMA_COLLECTION=profile-evidence-bge-m3
```

So werden alte und neue Embeddings getrennt gehalten. Bereits gespeicherte
Profil-Evidence muss anschließend mit dem neuen Modell neu eingebettet werden.

Ist `EMBEDDING_PROVIDER` deaktiviert oder kein API-Key gesetzt, bleibt das bestehende lexikalische Matching aktiv.

## Lokale Embeddings mit Ollama

Ollama stellt einen OpenAI-kompatiblen Embeddings-Endpunkt bereit. Für den
lokalen Betrieb mit Docker läuft Ollama normalerweise auf dem Host; deshalb
verwendet das Backend `host.docker.internal` statt `localhost`:

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=http://host.docker.internal:11434/v1
EMBEDDING_API_KEY=ollama
EMBEDDING_MODEL=bge-m3:latest
EMBEDDING_DIMENSION=1024
```

Der API-Key wird vom aktuellen OpenAI-kompatiblen Client technisch erwartet,
aber von Ollama nicht geprüft. Der Wert `ollama` ist daher ausreichend.
Für deutsche Stellenanzeigen ist `bge-m3` ein geeigneter lokaler Startpunkt.
Alternativ können `nomic-embed-text:latest` (typischerweise Dimension 768)
oder `nomic-embed-text-v2-moe:latest` verwendet werden. Die Dimension muss
immer der tatsächlichen Modellantwort entsprechen. Sie kann mit einem Test
gegen `http://localhost:11434/v1/embeddings` ermittelt werden.

Nach Änderungen an Modell oder Dimension müssen Backend und gegebenenfalls
die gespeicherten Profil-Evidence-Embeddings neu aufgebaut werden. Eine
Chroma-Collection darf nicht Embeddings verschiedener Dimensionen mischen.

## Datenfluss

Bei neuer Evidence wird der kontextuelle Text als Embedding erzeugt und in der Chroma-Collection gespeichert. Die Metadaten enthalten mindestens `profile_id` und `embedding_model`. Beim Matching wird das Requirement eingebettet, gegen Evidence desselben Profils gesucht und mit den lexikalischen Kandidaten zusammengeführt.

Die Similarity entscheidet nicht allein über die fachliche Erfüllung. Ein semantischer Treffer ohne lexikalischen Nachweis kann höchstens als verwandte bzw. teilweise Evidence bewertet werden.

## Migration

Es ist keine PostgreSQL-Migration für Vektoren erforderlich. Die frühere pgvector-Migration wurde entfernt, weil die verwendete Dify-PostgreSQL-Instanz die `vector`-Extension nicht enthält.
