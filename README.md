# OldschoolLife: Discord-News einrichten

Diese Vorlage veröffentlicht die beiden ausgewählten Discord-Kanäle als
öffentlichen Newsfeed für den Missionshelfer. Es ist kein eigener Webserver
und keine eigene Domain nötig. GitHub Pages liefert eine HTTPS-Adresse.

Die Vorlage ist vorbereitet; es wurde noch kein Bot, kein Repository und keine
Veröffentlichung für dich angelegt. Die folgenden Schritte erledigst du einmal
mit deinen eigenen Discord- und GitHub-Konten. Ein Bot-Token gehört nur in das
GitHub-Secret, niemals in den Missionshelfer, in ein hochgeladenes Dokument oder
in den Quellcode.

## 1. Discord-Bot anlegen

1. Öffne https://discord.com/developers/applications und melde dich an.
2. Klicke auf **New Application** und nenne sie z. B. **OldschoolLife News**.
3. Öffne **Bot**. Aktiviere unter **Privileged Gateway Intents** den Schalter
   **MESSAGE CONTENT INTENT**. Das wird auch für den Nachrichteninhalt über
   die HTTP-Schnittstelle benötigt.
4. Erzeuge/kopiere unter **Token** den Bot-Token. Du trägst ihn in Schritt 3
   ausschließlich als GitHub-Secret ein. Falls du ihn verloren hast, über
   **Reset Token** einen neuen erzeugen.
5. Kopiere unter **General Information** die **Application ID**.
6. Ersetze in dieser Adresse `DEINE_APPLICATION_ID` durch diese Zahl und öffne
   sie im Browser:

```text
https://discord.com/oauth2/authorize?client_id=DEINE_APPLICATION_ID&scope=bot&permissions=66560&guild_id=990645542260445254&disable_guild_select=true
```

7. Füge den Bot zu **eurem OldschoolLife-Server** hinzu. Benötigt werden
   **Kanal ansehen** und **Nachrichtenverlauf lesen**. Keine Administratorrechte.
8. Erlaube dem Bot diese beiden Rechte in den beiden Kanälen und verweigere
   dort **Nachrichten senden**. Der Exporter selbst implementiert ausschließlich
   lesende GET-Anfragen.

Voreingestellt sind exakt diese Kanäle:

- News: https://discord.com/channels/990645542260445254/997782407673544754
- Changelog: https://discord.com/channels/990645542260445254/997783396468142091

Der Bot kann in Discord **offline** angezeigt werden. Das ist bei dieser
Variante normal: Der Abruf benötigt keine dauerhafte Gateway-Verbindung.

## 2. Eigenes kleines GitHub-Repository anlegen

1. Melde dich bei https://github.com an.
2. Erstelle ein **neues, öffentliches Repository**, z. B. `oldschoollife-news`.
   Die Vorlage ist für öffentliche Repositories mit GitHub Free ausgelegt.
3. Entpacke `OldschoolLife-Discord-News-Einrichtung.zip` und lade **seinen Inhalt**
   in dieses neue Repository. `export_news.py` und `channels.json` müssen direkt
   im Hauptverzeichnis liegen, ebenso der Ordner `.github` mit dem Workflow.
   Nutze dafür einen getrennten Ordner, nicht das Arma-Serverfiles-Repository.
4. Die Dateien unter `site/` werden automatisch erstellt und nicht hochgeladen.

Der Feed ist öffentlich: Jeder mit seiner Adresse kann die exportierten
Beiträge lesen, auch ohne Mitglied im Discord-Server zu sein. Verwende diese
Vorlage nur für die beiden dafür vorgesehenen News-/Changelog-Kanäle.

## 3. Bot-Token sicher bei GitHub hinterlegen

1. Öffne im **neuen News-Repository** die **Settings**.
2. Unter **Secrets and variables → Actions**: **New repository secret**.
3. Name exakt: `DISCORD_BOT_TOKEN`.
4. Als Wert den Bot-Token aus Schritt 1 einsetzen und speichern.

Der Token steht damit nicht in veröffentlichten Dateien. Der Workflow gibt
keine Header oder rohen Discord-Fehlerantworten aus. Er wird nur auf dem
Standardbranch manuell oder zeitgesteuert gestartet, nicht durch Pull Requests.

## 4. Newsfeed veröffentlichen

1. Unter **Settings → Pages → Build and deployment → Source** die Auswahl
   **GitHub Actions** aktivieren.
2. Öffne den Reiter **Actions**, wähle **OldschoolLife Discord-News** und klicke
   auf **Run workflow**.
3. Warte, bis Abruf und Veröffentlichung grün sind. Bei einem Fehler die
   verständliche Meldung im Export-Schritt lesen (z. B. fehlendes Intent oder
   fehlende Kanalrechte).
4. Die veröffentlichte Adresse steht beim Deployment. Hänge `news.json` an,
   zum Beispiel:

```text
https://DEIN-GITHUB-NAME.github.io/oldschoollife-news/news.json
```

5. Öffne diese Adresse zur Kontrolle. Es muss JSON mit euren Beiträgen erscheinen.

Es werden die letzten 20 Beiträge je Kanal einschließlich Textinhalten von
Embeds abgeholt. Anhänge erscheinen als Dateinamen; das Original öffnest du in
Discord. Bearbeitete/gelöschte Beiträge werden beim nächsten Abruf neu eingelesen.

Der geplante Abruf läuft ungefähr alle 15 Minuten; GitHub kann Zeitpläne
verzögert ausführen. Ein Fehler ersetzt den vorher veröffentlichten Stand nicht.
Bei 60 Tagen ohne Repository-Aktivität kann GitHub den Zeitplan deaktivieren.
Dann unter **Actions** wieder aktivieren oder den Workflow manuell ausführen.
Es ist kein Echtzeit-Abonnement.

## 5. Adresse im Missionshelfer eintragen

1. Im Missionshelfer **News & Changelogs** öffnen.
2. **News-Adresse...** anklicken, die öffentliche `https://.../news.json`-Adresse
   eintragen und speichern.
3. Mit **Aktualisieren** prüfen. Danach lädt die Ansicht bei geöffnetem Programm
   regelmäßig den aktuellen Feed. Bei Verbindungsproblemen bleibt der letzte
   gespeicherte Stand mit Zeitangabe sichtbar.

Für alle Spieler kannst du die Adresse außerdem im Release neben der EXE in
`loader-settings.json` unter `NewsFeedUrl` eintragen und dieses ZIP verteilen.
Eine lokal unter **News-Adresse...** gespeicherte Adresse hat Vorrang.
Spieler benötigen weder einen Bot-Token noch eine Discord-Anmeldung im Programm.

## Testen und technische Hinweise

Python 3.11 oder neuer, keine zusätzlichen Pakete:

```text
python -m unittest discover -s tests -v
```

Die Tests verwenden lokale Beispieldaten und führen keine Discord-Anfragen aus.
Ein manueller Export liest den Token nur aus der Umgebungsvariable
`DISCORD_BOT_TOKEN`. Die Ausgabe enthält nur freigegebene Beiträge. Der
Missionshelfer rendert Texte ohne HTML/WebView und baut Beitragslinks selbst
aus den fest vorgegebenen Kanal-IDs auf.

Offizielle Dokumentation:

- Discord-Nachrichten: https://docs.discord.com/developers/resources/message#get-channel-messages
- Message Content Intent: https://docs.discord.com/developers/events/gateway#message-content-intent
- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- Geplante Workflows: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule
