import sys
import traceback

from utility import getAnimeClass, cleanProgram, customPrint

anime = None
try:
    if len(sys.argv) == 2:
        print(sys.argv[1])
        my_url = sys.argv[1]
        anime = getAnimeClass(my_url)
        if anime is not None:
            episodeList = anime.downloadAnime()
    else:
        while True:
            my_url = input("Inserisci l'url dell'anime da scaricare: ")
            anime = getAnimeClass(my_url)
            if anime is not None:
                episodeList = anime.downloadAnime()
                if episodeList is None:
                    print("Url non valido. Riprova")
                else:
                    print(episodeList)
                    break
                customPrint("Ho scaricato l'anime :" + anime.name)
            else:
                print("Url non valido. Riprova")
except KeyboardInterrupt:
    try:
        cleanProgram(anime.incomplete)
    except NameError:
        pass
except Exception:
    customPrint("Eccezione trovata")
    customPrint(traceback.format_exc())
    try:
        cleanProgram(anime.incomplete)
    except NameError:
        pass
