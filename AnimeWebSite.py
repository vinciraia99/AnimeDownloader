import array
import os
import string
import urllib
from urllib import request


class AnimeWebSite:

    def __init__(self, url):
        self.url = url
        self.incomplete = False
        self.airing = False
        self.name = None
        self.__indexanime = 1

    def __fixUrl(self, link: string, website: string):
        link = link.replace("///", "//")
        if website in link:
            try:
                split = link.split("/")
                link_filter = split[0]
                for i in range(1, 5):
                    link_filter += "/" + split[i]
                return link_filter
            except Exception:
                return None
        else:
            return None

    def downloadAnime(self, start, listEpisodi: array = None):
        from utility import progressBar
        if listEpisodi is None:
            listEpisodi = self.getEpisodeList(start)
        listAnimeDownloaded = []
        anime_name = self.__replaceNameDir()
        dir = self.__createOrCheckDowloadedFileDir(anime_name, listAnimeDownloaded)
        self.__createAiringFile(dir, self.url)
        self.__incomplete = self.__createIncompleteFile(dir, self.url)
        self.incomplete = True
        print("Scarico i " + str(len(listEpisodi)) + " episodi/o")
        i = 1
        for episodio in listEpisodi:
            splitEp = episodio["name"]
            print(str(i) + ". Avvio il download di: " + splitEp)
            if splitEp in listAnimeDownloaded:
                print(splitEp + " già trovato nei file scaricati")
            else:
                try:
                    request.urlretrieve(episodio["url"], os.path.join(dir, splitEp + ".tmp"), progressBar)
                    os.rename(os.path.join(dir, splitEp + ".tmp"), os.path.join(dir, splitEp))
                except (urllib.error.HTTPError, urllib.error.URLError):
                    return listEpisodi[i - 1:len(listEpisodi)]
            i += 1
        self.__removeIncompleteFile(self.__incomplete)
        return True

    def __removeIncompleteFile(self, incomplete):
        if os.path.exists(incomplete) == True:
            os.remove(incomplete)

    def __replaceNameDir(self):
        return self.name.replace(":", "").replace("\\", "").replace("/", "").replace(":", "").replace("*",
                                                                                                      "").replace(
            "?", "").replace("”", "").replace("<", "").replace(">", "").replace("|", "")

    def __createOrCheckDowloadedFileDir(self, anime_name, listAnimeDownloaded: array = []):
        dir = os.path.join(os.getcwd(), anime_name)
        if not os.path.exists(dir):
            os.mkdir(dir)
        else:
            for file in os.listdir(dir):
                if file.endswith(".mp4"):
                    listAnimeDownloaded.append(file)
        return dir

    def __createAiringFile(self, dir, link):
        airingurl = os.path.join(dir, ".url")
        if self.airing and os.path.exists(airingurl) == False:
            file = open(airingurl, 'w+')
            file.write(link)
            file.close()

    def __createIncompleteFile(self, dir, link):
        incomplete = os.path.join(dir, ".incomplete")
        if os.path.exists(incomplete) == False:
            file = open(incomplete, 'w+')
            file.write(link)
            file.close()
        return incomplete
