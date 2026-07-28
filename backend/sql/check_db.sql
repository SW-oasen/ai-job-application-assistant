docker exec -it docker-db_postgres-1 psql -U postgres -d application_assistant

-- Tabellen anzeigen
\dt

-- Gespeicherte Jobs anzeigen
SELECT id, title, source_type, source_url, source_filename,
       retrieval_method, imported_at
FROM jobs
ORDER BY imported_at DESC;

-- Anzahl der Jobs
SELECT COUNT(*) FROM jobs;

-- Einen Job vollständig ansehen
SELECT *
FROM jobs
WHERE id = 'DEINE-JOB-ID';

-- Importierten Inhalt ansehen
SELECT id, title, normalized_content
FROM jobs
ORDER BY imported_at DESC
LIMIT 1;

-- Nur URL-Importe
SELECT id, title, source_url
FROM jobs
WHERE source_type = 'url';

-- Nur PDF-Importe
SELECT id, source_filename, content_hash
FROM jobs
WHERE source_type = 'pdf';

-- psql verlassen
\q