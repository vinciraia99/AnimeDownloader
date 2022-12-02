import array
import string

import requests
from bs4 import BeautifulSoup

from AnimeWebSite import AnimeWebSite


class AnimeWorld(AnimeWebSite):

    def __init__(self, url: string):
        super(AnimeWorld, self).__init__(url)

    def __request(self, url: string):
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
        from utility import customPrint
        url = self._AnimeWebSite__fixUrl(self.url, "www.animeworld")
        if url is not None:
            self.__soup = self.__request(url)
            self.name = self.__getAnimeName()
            if self.name is None:
                return None
            self.__checkIsAiring()
            customPrint("Acquisisco gli episodi per l'anime: " + self.name)
            listEpisodiLink = self.__largeEpisodeFetch(start)
            listEpisodi = []
            self._AnimeWebSite__indexanime = start
            first = True
            for episodio in listEpisodiLink:
                episodiourl = "https://" + url.split("/")[2] + episodio.find("a")["href"]
                soap = self.__request(episodiourl)
                link = self.__findNewUrl(soap)
                if first:
                    findLinkFastList = self.__findUrlFastMode(link, len(listEpisodiLink))
                    if findLinkFastList is not None and len(findLinkFastList) == len(listEpisodiLink):
                        listEpisodi = findLinkFastList
                        break
                    first = False
                customPrint("Acquisito l'episodio " + str(self._AnimeWebSite__indexanime) + " di " + str(len(
                    listEpisodiLink)) + " : " + self.__getEpisodioNameFileFromUrl(link))
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
        from utility import customPrint
        episodeList = []
        indexAnime = self._AnimeWebSite__indexanime
        if self._AnimeWebSite__indexanime == 1:
            indexAnimeTotal = 0
        else:
            indexAnimeTotal = self._AnimeWebSite__indexanime
        for e in url.split("_"):
            try:
                if int(e) == indexAnime:
                    startingepg = e
                    break
            except ValueError:
                pass
        lenstartingepg = len(startingepg)
        for index in range(int(startingepg), lentotalepisodi + self._AnimeWebSite__indexanime):
            episodeNumber = str(index)
            indexlen = len(episodeNumber)
            if indexlen != lenstartingepg:
                for e in range(indexlen, lenstartingepg):
                    episodeNumber = "0" + episodeNumber
            url_download = url.replace(startingepg, episodeNumber)
            request = requests.head(url_download, headers={
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36'})
            if request.status_code == 200:
                customPrint("Acquisito l'episodio " + str(indexAnime) + " di " + str(
                    lentotalepisodi + indexAnimeTotal) + " : " + self.__getEpisodioNameFileFromUrl(url_download))
                episodeList.append(url_download)
                indexAnime += 1
            else:
                customPrint("Impossibile acquisire anime in modalità rapida, provo un altro modo")
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
