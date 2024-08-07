# AnimeDownloader

> If you are an English user please read the [README.en.md](README.en.md) file

## Info

Questo script in Python permette il download automatico di episodi di un anime dai seguenti siti:

* AnimeWorld

## Usage

Il file anime.py permette il download di un'intera stagione di un anime ricevendo in input l'url dell'anime da
scaricare. Esso è in grado di riceverlo in due modalità:

1.Richiesto a runtime

~~~~
Inserisci l'url dell'anime da scaricare: http://example.com
~~~~

2. Passato come argomento

~~~~
python anime.py http://example.com
~~~~

## Installazione

1. Download [Chrome](https://www.google.com/chrome/)
2. Installate [Python3](https://www.python.org/downloads/)
3. Scaricare il [repo](https://github.com/vinciraia99/AnimeDownloader/archive/refs/heads/main.zip) o in alternativa
   lanciate il comando `git clone https://github.com/vinciraia99/AnimeDownloader.git`
4. Installate requirements.txt file incluso nel repo: `pip install -r requirements.txt`.
5. Lanciare `python anime.py` per iniziare ad usare lo script
6. Per aggiornare anime in corso potete lanciare `python updater.py`

## Future implementazioni

* Supporto ad altri siti
* Supporto per più download contemporaneamente
* Supporto a ricevere in input un file con vari url di anime da scaricare
* Ricerca di anime all'interno dello script
* Possiblità di customizzare la cartella di output
