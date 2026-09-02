# Isolierte Demo-Umgebung

Die Demo läuft bewusst mit einer eigenen PostgreSQL-Datenbank, einem eigenen
Dokumenten-Volume und einer eigenen ChromaDB. Deshalb zeigt sie ausschließlich
die sechs fiktiven Stellenanzeigen. Echte Stellen aus der regulären Anwendung
werden nicht gelesen und können dort auch nicht verändert werden.

## Einmalig einrichten

1. Eine leere PostgreSQL-Datenbank `application_assistant_demo` anlegen. Sie
   darf nicht dieselbe Datenbank wie die reguläre Anwendung sein.
2. Die Vorlage kopieren:

   ```powershell
   Copy-Item .env.demo.example .env.demo
   ```

3. In `.env.demo` nur die Verbindungszeichenfolge dieser Demo-Datenbank bei
   `DATABASE_URL` eintragen. Der Datenbankname am Ende muss
   `application_assistant_demo` sein. Der Demo-Container verweigert den Start,
   wenn dieser Datenbankname nicht zu `DEMO_DATABASE_NAME` passt.
4. Demo starten und Daten erzeugen:

   ```powershell
   docker compose -f compose.demo.yaml up -d --build application-assistant-demo chromadb-demo
   docker compose -f compose.demo.yaml --profile tools run --rm demo-seed
   ```

5. Die Demo unter `http://localhost:8081/` öffnen. Die reguläre Anwendung
   bleibt unter `http://localhost:8080/` erreichbar.

Die bestehende `.env` darf die Dify- und MinerU-Zugangsdaten enthalten.
`compose.demo.yaml` lädt sie für die KI-Funktionen, überschreibt die
`DATABASE_URL` jedoch durch die isolierte `.env.demo`.

## Testerprofil auswählen

In der Demo unter **Verwaltung > Profil** im Dropdown `Demo Testerprofil`
auswählen und **Profil laden** drücken. Vor einem Live-Import kurz prüfen:

- Die Browser-Adresse beginnt mit `http://localhost:8081`.
- Der Profil-Chip im Kopfbereich zeigt `Demo Testerprofil`.
- Die Jobliste enthält nur die sechs fiktiven Firmen.

Das Seed-Profil enthält neutrale Beispieldaten und Skills. Falls für die
Präsentation dein bereits angelegtes Testerprofil benötigt wird, exportiere es
in der regulären Anwendung unter **Verwaltung > Profil** und importiere die
Datei anschließend ausschließlich in der Demo. Profil-Exporte enthalten keine
Stellenanzeigen; sie übertragen daher keine echten Jobs.

## Live-Import während der Präsentation

Ein echter Job kann in der Demo importiert, extrahiert und gematcht werden.
Er wird dabei nur in `application_assistant_demo` gespeichert. Die Dify- und
MinerU-Workflows erhalten natürlich den Inhalt dieser bewusst für die Demo
ausgewählten Anzeige, aber weder die Produktdatenbank noch deren Jobliste wird
berührt.

Das Seed-Skript kann jederzeit erneut ausgeführt werden. Es ergänzt nur
fehlende fiktive Stellen und überschreibt keine während der Demo importierten
Jobs.
