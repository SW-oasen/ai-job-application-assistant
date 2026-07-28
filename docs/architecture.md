# Architektur

## Verantwortlichkeiten

Der Application Assistant ist die stabile Kernanwendung. Dify und MinerU sind
austauschbare externe Dienste mit klaren HTTP-Schnittstellen.

```text
Dify (Orchestrierung und LLM)
  |
  | HTTP über Docker-DNS
  v
Application Assistant Backend
  |-- Import und Validierung
  |-- Geschäftslogik
  |-- Persistenz
  |
  |-- PostgreSQL
  |-- Redis
  `-- MinerU (OCR-Fallback)
```

Das Backend muss keine Dify- oder MinerU-Quelltexte importieren und keine
absoluten Pfade zu deren Repositories kennen. Service-Adressen kommen
ausschließlich aus Umgebungsvariablen.

## Lokale Netzwerkverbindung

Der Backend-Container tritt dem externen Netzwerk bei, in dem Dify und MinerU
laufen. Im derzeitigen lokalen Setup ist dies `docker_default`.

Interne Adressen:

| Dienst | Standardadresse |
|---|---|
| Application Assistant | `http://application-assistant-backend:8080` |
| Dify API | `http://api:5001` |
| MinerU | `http://mineru-api:8000` |
| PostgreSQL | `db_postgres:5432` |
| Redis | `redis:6379` |

Diese Werte sind konfigurierbare Defaults, keine fest verdrahteten
Container-IP-Adressen.

### Dify-SSRF-Proxy

Dify leitet HTTP-Request-Nodes durch seinen SSRF-Proxy. Damit dieser gezielt
das interne Backend erreichen kann, enthält die lokale Dify-`.env`:

```env
SSRF_PROXY_ALLOW_PRIVATE_DOMAINS=application-assistant-backend
```

Nach einer Änderung muss ausschließlich der Proxy neu erstellt werden:

```powershell
cd D:\Projects\AI\Dify\dify-main\docker
docker compose up -d --force-recreate ssrf_proxy
```

Die Freigabe darf nicht auf das gesamte private Netzwerk erweitert werden.

## Persistenz und Migrationen

Die Kernanwendung verwendet die eigene PostgreSQL-Datenbank
`application_assistant` auf der vorhandenen Instanz. Dify-Tabellen und
Dify-Datenbanken werden nicht verändert.

Die Verbindung wird ausschließlich über `DATABASE_URL` bereitgestellt. Das
lokale Geheimnis gehört in die ignorierte Datei `.env`; `.env.example` bleibt
die Vorlage ohne echtes Passwort. Migrationen werden aus dem Backend-Image
ausgeführt:

```powershell
docker compose run --rm application-assistant-backend alembic upgrade head
```

Die initiale Migration erzeugt Unternehmen, Stellen, Anforderungen,
Bewerbungen, generierte Dokumentversionen und Requirement-Matches. URL- und
PDF-Importe speichern Stellen anhand eines SHA-256-Content-Hashes. Ein erneut
importierter Inhalt liefert dieselbe `job_id` und `duplicate: true`.

Migration `20260723_0002` ergänzt strukturierte Profilquellen und einzelne
Evidenzbausteine. Das Matching speichert zu jeder Anforderung Match-Level,
Quellenbelege, Erklärung, Handlungsempfehlung und Confidence. Professionelle
Erfahrung und übertragbare Projekt-, Trainings- oder Bildungserfahrung bleiben
dabei ausdrücklich getrennt.

Migration `20260723_0003` ergänzt die kanonische Profilverwaltung. Skills,
Berufserfahrungen, Ausbildungen, Zertifikate und Referenzen bleiben editierbar,
besitzen DE/EN-Lokalisierungen und erzeugen bei jeder Änderung einen
unveränderlichen Revisionssnapshot.

Migration `20260728_0014` ergänzt Metadaten für tatsächlich versendete
Bewerbungsunterlagen. Die PDF-Dateien selbst liegen nicht in PostgreSQL,
sondern zentral unter `APPLICATION_DOCUMENTS_PATH`. In der Datenbank werden
nur der relative Storage-Key, Dokumentart, Originalname, Größe, SHA-256 und
Zeitpunkte gespeichert. Im Docker-Setup persistiert dafür das benannte Volume
`application-documents`; es muss gemeinsam mit der Datenbank gesichert werden.

## Upgrade-Grenzen

- Dify-Upgrades verändern die Kernanwendung nicht, solange die verwendeten
  Workflow- und HTTP-Verträge kompatibel bleiben.
- MinerU-Upgrades verändern die Kernanwendung nicht, solange dessen Client-
  Adapter die verwendete API-Version unterstützt.
- Workflow-DSLs werden versioniert exportiert und manuell in Dify importiert.
- Datenbankschemaänderungen erfolgen ausschließlich über Alembic-Migrationen.
