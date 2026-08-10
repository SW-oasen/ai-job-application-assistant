# Hybrid Search mit ChromaDB

Die Anwendung speichert relationale Profildaten und Matching-Ergebnisse weiterhin in PostgreSQL. Vektor-Embeddings der Profilevidence werden getrennt in ChromaDB gespeichert. Dadurch muss die bestehende Dify-PostgreSQL-Datenbank nicht durch eine pgvector-fähige Variante ersetzt werden.

## Betrieb

`docker compose up -d --build` startet zusätzlich den Dienst `chromadb`. Die Daten liegen im Volume `chroma-data`.

Die relevanten Einstellungen sind:

```env
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_KEY=...
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
CHROMA_HOST=chromadb
CHROMA_PORT=8000
CHROMA_COLLECTION=profile-evidence
```

Ist `EMBEDDING_PROVIDER` deaktiviert oder kein API-Key gesetzt, bleibt das bestehende lexikalische Matching aktiv.

## Datenfluss

Bei neuer Evidence wird der kontextuelle Text als Embedding erzeugt und in der Chroma-Collection gespeichert. Die Metadaten enthalten mindestens `profile_id` und `embedding_model`. Beim Matching wird das Requirement eingebettet, gegen Evidence desselben Profils gesucht und mit den lexikalischen Kandidaten zusammengeführt.

Die Similarity entscheidet nicht allein über die fachliche Erfüllung. Ein semantischer Treffer ohne lexikalischen Nachweis kann höchstens als verwandte bzw. teilweise Evidence bewertet werden.

## Migration

Es ist keine PostgreSQL-Migration für Vektoren erforderlich. Die frühere pgvector-Migration wurde entfernt, weil die verwendete Dify-PostgreSQL-Instanz die `vector`-Extension nicht enthält.
