import sys
import traceback

from AnimeWebSite import AnimeWebSite
from utility import initDriver, getAnimeClass, cleanProgram

try:
    if len(sys.argv) == 2:
        print(sys.argv[1])
        my_url = sys.argv[1]
        anime = getAnimeClass(my_url)
        if anime is not None:
            episodeList = anime.downloadAnime(my_url)
    else:
        while True:
            my_url = input("Inserisci l'url dell'anime da scaricare: ")
            anime = getAnimeClass(my_url)
            if anime is not None:
                episodeList = anime.downloadAnime(my_url)
                if episodeList is None:
                    print("Url non valido. Riprova")
                else:
                    print(episodeList)
                    break
            else:
                print("Url non valido. Riprova")
    print("Fatto!")
except KeyboardInterrupt:
    try:
        cleanProgram(driver, anime.incomplete)
    except NameError:
        cleanProgram(driver, False)
except Exception:
    print(traceback.format_exc())
    try:
        cleanProgram(driver, anime.incomplete)
    except NameError:
        cleanProgram(driver, False)
