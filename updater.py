import traceback
import warnings

from utility import *

warnings.filterwarnings("ignore")


def getMp4Element(dirname):
    mp4 = []
    for file in os.listdir(os.path.join(os.getcwd(), dirname)):
        if file.endswith(".mp4"):
            mp4.append(file)
    return mp4


def isAllAviable(dirname):
    mp4 = getMp4Element(dirname)
    if len(mp4) > 0:
        mp4.sort()
        prec = int(mp4[0].split("_")[2])
        for i in range(1, len(mp4)):
            if int(mp4[i].split("_")[2]) == prec + 1:
                prec = int(mp4[i].split("_")[2])
            else:
                return False
    else:
        return False
    return True


def deleteAiring(dirname):
    path = os.path.join(os.getcwd(), dirname)
    if os.path.isdir(path):
        for file in os.listdir(path):
            if file == ".url" or file == "url":
                os.remove(os.path.join(path, file))
                return True
    return False


def readFileUrl():
    file = ""
    if os.path.isfile(os.path.join(os.getcwd(), dir, ".url")):
        file = open(os.path.join(os.getcwd(), dir, ".url"), "r")
    elif os.path.isfile(os.path.join(os.getcwd(), dir, ".incomplete")):
        file = open(os.path.join(os.getcwd(), dir, ".incomplete"), "r")
    elif os.path.isfile(os.path.join(os.getcwd(), dir, "url")):
        file = open(os.path.join(os.getcwd(), dir, "url"), "r")
    return file


def findFileUrl():
    listDir = []
    for path in os.listdir(os.getcwd()):
        if os.path.isdir(path):
            for subpath in os.listdir(os.path.join(os.getcwd(), path)):
                if subpath == ".url" or subpath == ".incomplete" or subpath == "url":
                    if subpath not in listDir:
                        listDir.append(path)
    return listDir


airing = False
status = False
listDir = findFileUrl()
listUrl = []
updated = []
for dir in listDir:
    file = readFileUrl()
    dict = {
        "name": dir,
        "url": file.read(),
        "episodi": len(getMp4Element(dir))

    }
    listUrl.append(dict)
    file.close()
animeindex = 1
status = True
try:
    for dict_url in listUrl:
        try:
            print("== Verifico se ci sono nuovi episodi per l'anime " + str(animeindex) + " di " + str(
                len(listUrl)) + " : " +
                  dict_url["name"] + " ==")
            animeindex += 1
            my_url = dict_url["url"]
            anime = getAnimeClass(my_url)
            if anime is not None:
                if isAllAviable(dict_url["name"]):
                    episodeList = anime.getEpisodeList(dict_url["episodi"])
                else:
                    episodeList = anime.getEpisodeList()
            if len(episodeList) > 0:
                anime.downloadAnime(0, episodeList)
                updated.append(anime.name)
            else:
                print("Non ci sono nuovi episodi")
            if anime.airing == False and deleteAiring(dict_url["name"]):
                print("L'anime " + anime.name + " non è più in corso")
        except IndexError:
            print(
                "L'anime " + dict_url[
                    "name"] + " ha generato un errore, l'errore potrebbe essere causato dal nome modificato manualmente di un anime, per favore ripristina il nome e rilancia lo script ")
            print(traceback.format_exc())
    status = False
    if len(updated) > 0:
        text = "\nHo aggiornato i seguenti anime:"
        for e in updated:
            text += "\n" + e
        customPrint(text)
    else:
        customPrint("\nNessun nuovo episodio anime tra quelli in lista")
except KeyboardInterrupt:
    try:
        cleanProgram(anime)
    except NameError:
        pass
except Exception:
    customPrint("Eccezione trovata")
    customPrint(traceback.format_exc())
    try:
        cleanProgram(anime)
    except NameError:
        pass
