import array
import string

import requests
from bs4 import BeautifulSoup

from AnimeWebSite import AnimeWebSite


class AnimeWorld(AnimeWebSite):

    def __init__(self, url: string):
        self.__soup = None
        super(AnimeWorld, self).__init__(url)

    def __requestSoup(self, url: string):
        request = requests.request("GET", url)
        return BeautifulSoup(request.content, "html.parser")

    def __findNewUrl(self, soap):
        parent = soap.find("div", class_="downloads")
        listLink = parent.findAll("a")
        for link in listLink:
            href = link['href']
            if ".mp4" in href and not ".php" in href:
                return href

    def __largeEpisodeFetch(self, start: int) -> array:
        servertabfinder = self.__soup.findAll("span", class_="server-tab")
        id = ""
        parent = ""
        for server in servertabfinder:
            if "AnimeWorld" in server.text:
                id = server['data-name']
                break
        serverfinder = self.__soup.findAll("div", class_="server")
        for server in serverfinder:
            if str(id) == server['data-name']:
                parent = server
                break
        episodiTab = parent.findAll("li", class_="episode")
        return episodiTab[start - 1:len(episodiTab)]

    def __getAnimeName(self) -> string:
        title = self.__soup.find(id="anime-title")
        return title.text

    def getEpisodeList(self, start: int = 1) -> array:
        if start != 1:
            start = start + 1
        url = self._AnimeWebSite__fixUrl(self.url, "www.animeworld")
        if url is not None:
            try:
                self.__soup = self.__requestSoup(url)
                self.name = self.__getAnimeName()
            except Exception:
                return None
            self.__checkIsAiring()
            print("Acquisisco gli episodi per l'anime: " + self.name)
            listEpisodiLink = self.__largeEpisodeFetch(start)
            listEpisodi = []
            self._AnimeWebSite__indexanime = start
            first = True
            if len(listEpisodiLink) == start:
                # Fix Updater
                return listEpisodi
            for episodio in listEpisodiLink:
                lenlistEpisodiLink = len(listEpisodiLink) - 1
                lentotalEpisodi = lenlistEpisodiLink + start
                episodiourl = "https://" + url.split("/")[2] + episodio.find("a")["href"]
                soap = self.__requestSoup(episodiourl)
                link = self.__findNewUrl(soap)
                if first:
                    findLinkFastList = self.__findUrlFastMode(link, lenlistEpisodiLink)
                    if findLinkFastList is not None and len(findLinkFastList) == (lenlistEpisodiLink + 1):
                        listEpisodi = findLinkFastList
                        break
                    else:
                        print("Acquisizione dei link in modalità rapida fallita. Provo in un'altro modo")
                    first = False
                print("Acquisito l'episodio " + str(self._AnimeWebSite__indexanime) + " di " + str(
                    lentotalEpisodi) + " : " + self.__getEpisodioNameFileFromUrl(link))
                self._AnimeWebSite__indexanime += 1
                listEpisodi.append(link)
            result = listEpisodi
            if result is not None:
                listDictEpisodi = []
                for episodio in result:
                    dict = {
                        'url': episodio,
                        'name': self.__getEpisodioNameFileFromUrl(episodio)
                    }
                    listDictEpisodi.append(dict)
                return listDictEpisodi
            else:
                return None
        else:
            return None

    def __checkIsAiring(self):
        for item in self.__soup.findAll("dd"):
            if "In corso" in item.text:
                self.airing = True

    def __findUrlFastMode(self, url: string, lentotalepisodi: int):
        episodeList = []
        indexAnime = self._AnimeWebSite__indexanime
        indexAnimeString = self._AnimeWebSite__indexanime
        indexAnimeTotal = self._AnimeWebSite__indexanime
        startingepg = None
        for e in url.split("_"):
            try:
                if indexAnime - 1 == int(e):
                    indexAnime -= 1
                if int(e) == indexAnime:
                    startingepg = e
                    break
            except ValueError:
                pass
        if startingepg is None:
            return None
        lenstartingepg = len(startingepg)
        for index in range(int(startingepg),
                           lentotalepisodi + self._AnimeWebSite__indexanime + 1 - (indexAnimeString - indexAnime)):
            episodeNumber = str(index)
            indexlen = len(episodeNumber)
            if indexlen != lenstartingepg:
                for e in range(indexlen, lenstartingepg):
                    episodeNumber = "0" + episodeNumber
            url_download = url.replace(startingepg, episodeNumber)
            request = requests.head(url_download, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36'})
            if request.status_code == 200:
                print("Acquisito l'episodio " + str(indexAnimeString) + " di " + str(
                    lentotalepisodi + indexAnimeTotal) + " : " + self.__getEpisodioNameFileFromUrl(url_download))
                episodeList.append(url_download)
                indexAnime += 1
                indexAnimeString += 1
            else:
                print("Impossibile acquisire anime in modalità rapida, provo un altro modo")
                return None
        return episodeList

    def __getEpisodioNameFileFromUrl(self, url: string):
        array = url.split("/")
        for word in array:
            if word.endswith(".mp4"):
                return word

    def downloadAnime(self, start: int = 1, listEpisodi: array = None):
        listEpisodi = super().downloadAnime(start, listEpisodi)
        if listEpisodi != True:
            raise Exception("Download fallito, potrebbe essere un prpoblema di rete")
        return listEpisodi
