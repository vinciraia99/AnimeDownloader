# AnimeDownloader

## Warning

This tool has not yet been translated into English, and the currently supported sites only contain Italian anime.

## Info

This script in Python allows automatic downloading of anime episodes from the following sites:

* AnimeWorld

## Usage

The anime.py file allows the download of an entire season of an anime by receiving as input the url of the anime to be
downloaded. It is able to receive it in two ways:

1.Required at runtime

~~~~
Inserisci l'url dell'anime da scaricare: http://example.com
~~~~

2. Passed as argument

~~~~
python anime.py http://example.com
~~~~

## Installation

1. Download [Chrome](https://www.google.com/chrome/)
2. Install [Python3](https://www.python.org/downloads/)
3. Download the [repo](https://github.com/vinciraia99/AnimeDownloader/archive/refs/heads/main.zip) or alternatively run
   the command `git clone https://github.com/vinciraia99/AnimeDownloader.git
4. Install requirements.txt file included in the repo: `pip install -r requirements.txt`.
5. Run `python anime.py` to start using the script
6. To update current anime you can run `python updater.py`.

## Future implementations

* Support for other sites
* Support for multiple simultaneous downloads
* Support for receiving as input a file with various anime urls to download
* Search for anime within the script
* Possibility to customise the output folder



