import traceback
import warnings
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
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
            if file == ".url":
                os.remove(file)
                return True
    return False


airing = False
status = False
listDir = []
listUrl = []
updated = []
driver = None
# try:
for path in os.listdir(os.getcwd()):
    if os.path.isdir(path):
        for subpath in os.listdir(os.path.join(os.getcwd(), path)):
            if subpath == ".url" or subpath == ".incomplete" and subpath == "url":
                listDir.append(path)

for dir in listDir:
    file = open(os.path.join(os.getcwd(), dir, ".url"), "r")
    dict = {
        "name": dir,
        "url": file.read(),
        "episodi": len(getMp4Element(dir))

    }
    listUrl.append(dict)
    file.close()
animeindex = 1
driver = initDriver()
status = True
for dict_url in listUrl:
    try:
        print("== Verifico se ci sono nuovi episodi per l'anime " + str(animeindex) + " di " + str(
            len(listUrl)) + " : " +
              dict_url["name"] + " ==")
        animeindex += 1
        my_url = dict_url["url"]
        anime = getAnimeClass(my_url, driver)
        if anime is not None:
            if isAllAviable(dict_url["name"]):
                episodeList = anime.getEpisodeList(my_url, dict["episodi"]+1)
            else:
                episodeList = anime.getEpisodeList(my_url)
            updated.append(anime.name)
        if len(episodeList) > 0:
            anime.downloadAnime(my_url, 0, episodeList)
        else:
            print("Non ci sono nuovi episodi")
        if anime.airing == False and deleteAiring(dict["name"]):
            print("L'anime " + anime.name + " non è più in corso")
    except IndexError:
        print(
            "L'anime " + dict_url[
                "name"] + " ha generato un errore, l'errore potrebbe essere causato dal nome modificato manualmente di un anime, per favore ripristina il nome e rilancia lo script ")
        print(traceback.format_exc())
print("Chiudo la sessione di Chrome...")
driver.quit()
status = False
if len(updated) > 0:
    text = "Ho aggiornato i seguenti anime:"
    for e in updated:
        text += "\n" + e
    sendTelegram(text)
else:
    sendTelegram("Nessun nuovo episodio anime tra quelli in lista")
