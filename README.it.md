<div align="center">

# 🌀 VoidLoop

### Sparatutto arcade di cyber-sopravvivenza in un vuoto digitale infinito

[English](README.md) · **Italiano**

![Schermata del titolo](docs/screenshots/01_title.png)

</div>

## Scarica e gioca

Scarica la versione per il tuo sistema dalla pagina **[Releases](../../releases)** (oppure dagli artifact di *Actions → Build & release*):

| Sistema | File | Come |
|---------|------|------|
| **Windows** | `VoidLoop-…-windows-x64.msi` | Installer con scorciatoie in Start/Desktop e disinstallazione. |
| **Windows** | `VoidLoop-…-windows-x64.exe` | Portatile, un solo file: doppio clic. |
| **Linux** | `VoidLoop-….AppImage` | `chmod +x` e avvia. |
| **Linux** | `voidloop_….deb` | `sudo apt install ./voidloop_….deb` (Debian, Ubuntu, Mint…). |
| **Linux** | `VoidLoop-…-linux-x86_64.tar.gz` | Estrai, avvia `VoidLoop/VoidLoop` oppure `./install.sh` (installazione utente). |

> Su Windows può comparire l'avviso *SmartScreen* perché i file non sono firmati: scegli **Maggiori informazioni → Esegui comunque**.

**Da sorgente** (qualsiasi sistema, Python 3.8+):

```bash
git clone https://github.com/BitJacker/VoidLoop.git && cd VoidLoop
pip install -r requirements.txt
python play.py
```

Salvataggi e impostazioni stanno nella cartella utente (`%APPDATA%\VoidLoop`, `~/.local/share/voidloop`). Un vecchio salvataggio della versione 3 viene importato da solo.

## Novità della 4.0

- **Niente più finestra di avvio**: menu, opzioni e lingua sono dentro il gioco; finestra ridimensionabile e schermo intero (`F11`).
- **6 settori** con sfondo animato, musica, palette e un pericolo che cambia il modo di giocare: Settore Avvio, Flusso Dati (correnti), Firewall (cancelli laser), Cache Ghiacciata (ghiaccio scivoloso e stalattiti), Nucleo Corrotto (portali e glitch), Il Vuoto (pozzi gravitazionali).
- **6 boss** a più fasi con attacchi segnalati, **6 tipi di nemici** più le versioni élite.
- **Punti vita, scatto con invulnerabilità, corsa a stamina, Impulso** caricato sfiorando i proiettili, combo, tremore dello schermo.
- **Arsenale** tra gli stage: armi (doppio, ventaglio, perforante) e potenziamenti; **8 power-up**.
- **Una vera storia** in 4 lingue: dialoghi con ritratti animati, radio di bordo durante il gioco, cartelli di settore e **due finali**; poi New Game+.
- **19 obiettivi**, statistiche e record per modalità. **Audio sintetizzato dal gioco stesso** (nessun file audio).
- **Co-op** a 2 giocatori con tasto di fuoco anche per il giocatore 2. Corretti vari bug (nemici lenti che non andavano a destra/giù, proiettili storti, Controrelogio senza orologio, progressi condivisi tra modalità).

## Modalità

🎬 **Storia** (6 settori × 4 stage, boss finale, due finali) · ♾️ **Infinita** · ⏱️ **Controrelogio** (3 minuti) · 🦸 **Assalto ai boss** · 🌊 **Orda** (10 ondate con mazza al plasma). Difficoltà: Facile (5 PV), Normale (3), Difficile (2), Incubo (1).

## Comandi

| | Giocatore 1 | Giocatore 2 |
|-|-------------|-------------|
| Movimento | `W A S D` (anche frecce se giochi da solo) | Frecce |
| Mira / fuoco | Mouse / clic sinistro (o `Invio` = mira automatica) | `Invio` / `Num 0` |
| Scatto | `Maiusc sinistro` | `Maiusc destro` |
| Corsa | `Ctrl sinistro` | `Ctrl destro` |
| Impulso | `Spazio` | `Alt destro` / `Num .` |
| Arma | `1-4`, `Q`/`E`, rotella | come P1 |
| Pausa · Schermo intero · Muto | `Esc`/`P` · `F11` · `M` | |

## Costruire i pacchetti

Lo fa GitHub Actions a ogni push (`.github/workflows/build.yml`). Per pubblicare una release: unisci su `main`, poi **Actions → Build & release → Run workflow** con *publish* spuntato (oppure crea il tag `v4.0.0`).

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q          # test (senza schermo)
python play.py --selftest          # auto-verifica (funziona anche nei pacchetti)
bash packaging/linux/build.sh all  # Linux: tar.gz, .deb, AppImage -> out/
./packaging/windows/build.ps1      # Windows (PowerShell): .exe portatile + .msi -> out/
```

## Licenza

© 2026 BitJacker – tutti i diritti riservati, vedi [LICENSE](LICENSE). Componenti di terze parti in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
