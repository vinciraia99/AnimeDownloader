# AnimeDownloader

> If you are an English user please read the [README.en.md](README.en.md) file

## Info

Questo script in Python permette il download automatico di episodi di un anime dai seguenti siti:

- AnimeWorld - Ringrazio il dev della libreria [AnimeWorld-API](https://github.com/MainKronos/AnimeWorld-API)

## Usage

Il file `anime.py` permette il download di un'intera stagione di un anime ricevendo in input l'URL dell'anime da scaricare.

Può ricevere l'URL in due modalità:

### 1. Richiesto a runtime

```text
Inserisci l'url dell'anime da scaricare: https://example.com
```

### 2. Passato come argomento

```bash
python anime.py "https://example.com"
```

### 3. Passato come argomento con numero di worker

```bash
python anime.py "https://example.com" --max-workers=9
```

Sono supportate entrambe le forme seguenti:

```bash
python anime.py "https://example.com" --max-workers=9
python anime.py "https://example.com" --max-worker=9
```

Se l'URL non viene passato da riga di comando, lo script entra in modalità interattiva e lo richiede a terminale.

## updater.py

Il file `updater.py` controlla gli anime già tracciati tramite i file `.url`, `.incomplete` o `url` presenti nelle cartelle locali.

Lo script:

- legge gli anime già scaricati dal disco;
- estrae i numeri episodio dai file `.mp4`;
- controlla se esistono nuovi episodi online;
- scarica solo gli episodi mancanti o successivi;
- passa automaticamente alla directory successiva in caso di errore.

### Uso base

```bash
python updater.py
```

### Uso con numero di worker

```bash
python updater.py --max-workers=9
```

Anche qui sono supportate entrambe le forme:

```bash
python updater.py --max-workers=9
python updater.py --max-worker=9
```

## Parametri disponibili

| Script | Parametro | Descrizione |
|---|---|---|
| `anime.py` | `URL` | URL dell'anime da scaricare |
| `anime.py` | `--max-workers` / `--max-worker` | Numero massimo di download paralleli |
| `updater.py` | `--max-workers` / `--max-worker` | Numero massimo di download paralleli durante l'aggiornamento |

## Installazione

1. Installate [Python 3](https://www.python.org/downloads/).
2. Scaricate il [repo](https://github.com/vinciraia99/AnimeDownloader/archive/refs/heads/main.zip) oppure clonate con:

```bash
git clone https://github.com/vinciraia99/AnimeDownloader.git
```

3. Installate il file `requirements.txt` incluso nel repo:

```bash
pip install -r requirements.txt
```

4. Lanciate `python anime.py` per iniziare ad usare lo script.
5. Per aggiornare gli anime in corso potete lanciare `python updater.py`.

## Esempi rapidi

```bash
python anime.py "https://www.animeworld.ac/play/farming-life-in-another-world-2.SV5W0/h7ORaq0xHW"
python anime.py "https://www.animeworld.ac/play/farming-life-in-another-world-2.SV5W0/h7ORaq0xHW" --max-workers=9
python updater.py --max-workers=9
```
