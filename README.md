# Wohnungssuche Regensburg

Sucht automatisch nach Mietwohnungen in Regensburg, bewertet jede Anzeige und schickt
**jeden Morgen um 8:00** die neuen Treffer als Push aufs Handy, mit Foto, Beschreibung
und Ranking. Dazu gibt es eine App mit allen aktuellen Angeboten.

Es läuft komplett auf GitHub. Dein Mac muss dafür nicht laufen, und es fallen keine
API- oder Token-Kosten an.

## Was es macht

| | |
|---|---|
| **Quellen** | WG-Gesucht (1-Zimmer & Wohnungen), Kleinanzeigen (Mietwohnungen, nur Angebote) |
| **Filter** | max. 600 € warm · ab 20 m² · keine Tauschwohnungen · keine WG-Zimmer · keine Zwischenmiete unter 6 Monaten |
| **Wann** | 3× täglich suchen (≈ 6, 12, 18 Uhr) · Zusammenfassung um **8:00** · Top-Treffer (≥ 80 Punkte) sofort |
| **Push** | ein Push pro Wohnung (Foto, Miete, m², Lage, Pro/Contra, Beschreibung, Buttons) + Zusammenfassung |
| **App** | Ranking, Fotos, Bewertungs-Details, Favoriten, Karte, „Ausblenden“; installierbar auf dem Homescreen |

### Bewertung (0–100 Punkte)

| Kriterium | Punkte | Wie |
|---|---|---|
| Lage | 35 | Entfernung zum Neupfarrplatz: bis 1 km volle Punkte, ab 6 km 0 |
| Platz für deine Möbel | 30 | Bett 160×200, Schrank, Schreibtisch, 2er-Couch, TV-Board, Regal brauchen inkl. Küche/Bad ca. **24 m²**; darunter wird es eng, ab ~44 m² volle Punkte, +Bonus für separates Schlafzimmer |
| Preis | 25 | bis 420 € warm volle Punkte, bei 600 € noch ¼ |
| Ausstattung | 10 | Einbauküche, Balkon, Keller, Waschmaschine, Fahrradkeller, unbefristet |
| Abzüge | – | möbliert (deine Möbel passen dann nicht rein), Untermiete, befristet, „nur Wochenendheimfahrer“, eingeschränkter Mieterkreis, Ablöse, keine Fotos |
| KI (optional) | ±10 | Claude liest den Anzeigentext: Grundriss, Dachschrägen, Betrugsverdacht, versteckte Kosten |

🔥 Top ≥ 80 · ✅ Gut ≥ 65 · 🙂 Okay ≥ 50 · 😐 Mäßig

Alle Kriterien stehen in [`config.yaml`](config.yaml) und lassen sich dort ändern.

## So funktioniert's

```
GitHub Actions (3× täglich, kostenlos)
 ├─ collect   → WG-Gesucht + Kleinanzeigen lesen, filtern, bewerten → data/*.json (ins Repo committet)
 ├─ ai-queue  → (optional) Claude bewertet neue Anzeigen über dein Claude-Abo
 ├─ notify    → ntfy-Push: Zusammenfassung für 08:00 eingeplant, Top-Treffer sofort
 └─ export    → App bauen (Vue 3 + TypeScript) → GitHub Pages
```

- `src/wohnungssuche/`: Python-Kern (Scraper, Bewertung, Push)
- `web/`: App (Vue 3 + TS + Vite, PWA)
- `data/`: Datenbank als JSON (wird vom Bot gepflegt)
- `prompts/ki-bewertung.md`: Anweisungen für die optionale KI-Bewertung
- `tests/`: Tests (`pytest`)

---

## Einmalige Einrichtung

### Für Astra (am Computer, ca. 5 Minuten)

1. **Branch umbenennen (optional, aber sauberer)**: Der Code liegt auf dem Standard-Branch
   `claude/intelligent-galileo-t9xdb6`; die Zeitpläne laufen dort schon. Unter
   *Settings → General → Default branch* per Stift-Symbol in `main` umbenennen.
2. **Repo öffentlich machen** (nötig für die kostenlose App-Seite auf GitHub Pages):
   *Settings → General → Danger Zone → Change visibility → Public.*
   Es liegen keine Geheimnisse im Code; der Push-Kanal ist ein Secret.
   (Alternative: GitHub Pro, dann kann es privat bleiben.)
3. **GitHub Pages einschalten**: *Settings → Pages → Build and deployment → Source: **GitHub Actions***.
4. **Secret für die Push-Nachrichten** anlegen: *Settings → Secrets and variables → Actions → New repository secret*
   - Name: `NTFY_TOPIC`
   - Wert: der geheime Kanalname, den Niklas bekommen hat (nicht hier ins Repo schreiben!)
5. **Testen**: *Actions → Wohnungssuche → Run workflow*, Haken bei „Nur eine Testnachricht“ → Run.
   Auf Niklas' Handy muss „✅ Wohnungssuche ist verbunden“ ankommen.
   Danach noch einmal **ohne** Haken starten: das ist der erste echte Lauf, und die App geht online.

Per Terminal geht das auch (mit `gh`):

```bash
gh api -X POST repos/Explosis173/Wohnungssuche/branches/claude%2Fintelligent-galileo-t9xdb6/rename -f new_name=main
gh repo edit Explosis173/Wohnungssuche --visibility public --accept-visibility-change-consequences
gh api -X POST repos/Explosis173/Wohnungssuche/pages -f build_type=workflow
gh secret set NTFY_TOPIC --repo Explosis173/Wohnungssuche   # Wert eingeben
gh workflow run wohnungssuche.yml --repo Explosis173/Wohnungssuche -f test_push=true
gh workflow run wohnungssuche.yml --repo Explosis173/Wohnungssuche
```

#### Optional: KI-Bewertung über das Claude-Abo (keine API-Kosten)

Auf dem Mac, auf dem Claude Code eingeloggt ist:

```bash
claude setup-token
```

Den ausgegebenen Token als Secret `CLAUDE_CODE_OAUTH_TOKEN` speichern
(`gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo Explosis173/Wohnungssuche`).
Ab dann bewertet Claude neue Anzeigen zusätzlich (Grundriss, Betrugsverdacht, versteckte Kosten).
Das zählt gegen die Nutzungslimits des Abos, nicht gegen ein API-Budget. Ohne Secret wird
der Schritt einfach übersprungen.

### Für Niklas (am Handy, 2 Minuten)

1. App **ntfy** installieren ([iOS](https://apps.apple.com/app/ntfy/id1625396347) / [Android](https://play.google.com/store/apps/details?id=io.heckel.ntfy)).
2. In ntfy auf **+** tippen und den geheimen Kanalnamen eintragen (Server: `ntfy.sh`).
3. Die App-Seite **https://explosis173.github.io/Wohnungssuche/** in Safari öffnen →
   Teilen → **Zum Home-Bildschirm**. Dann ist das Ranking eine eigene App auf dem Homescreen.

Fertig. Ab jetzt kommt jeden Morgen um 8:00 die Zusammenfassung.

---

## Wenn etwas nicht klappt

- **Push „⚠️ Wohnungssuche: Aktion nötig“**: Ein Portal liefert seit 3 Läufen keine Daten
  (Seite umgebaut oder Abruf blockiert). Astra bittet Claude in diesem Repo:
  *„Der Scraper für <Portal> ist kaputt, bitte reparieren.“*
- **Gar keine Pushes**: unter *Actions* nachsehen, ob der Lauf rot ist. Häufigste Ursache:
  `NTFY_TOPIC` fehlt oder ist falsch geschrieben.
- **App-Seite 404**: Pages ist nicht auf „GitHub Actions“ gestellt (Schritt 3) oder das Repo ist privat.
- GitHub pausiert Zeitpläne nach 60 Tagen ohne Aktivität im Repo. Weil der Bot täglich Daten
  committet, passiert das hier nicht.

## Lokal entwickeln

```bash
pip install -e ".[dev]"
python -m pytest
python -m wohnungssuche collect        # echte Suche (schreibt nach data/)
python -m wohnungssuche notify         # ohne NTFY_TOPIC: Pushes nur auf der Konsole
python -m wohnungssuche export && (cd web && npm install && npm run dev)
```
