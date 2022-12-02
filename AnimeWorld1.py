import array
import os
import string


import requests
import wget
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement
from bs4 import BeautifulSoup

from AnimeWebSite import AnimeWebSite

import http.client


class AnimeWorld1(AnimeWebSite):

    def __request(self,url :string):
        request = requests.request("GET", url)
        return BeautifulSoup(request.content, "html.parser")

    def __findNewUrl(self,soap):
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
            return episodiTab[start:len(episodiTab)]

    def __getAnimeName(self) -> string:
        title = self.__soup.find(id="anime-title")
        return title.text

    def getEpisodeList(self, link: string, start: int = 0) -> array:
        from utility import customPrint
        url = self._AnimeWebSite__fixUrl(link, "www.animeworld")
        if url is not None:
            self.__soup = self.__request(url)
            self.name = self.__getAnimeName()
            if self.name is None:
                return None
            self.__checkIsAiring()
            customPrint("Acquisisco gli episodi per l'anime: " + self.name)
            listEpisodiLink = self.__largeEpisodeFetch(start)
            listEpisodi = []
            first = True
            for episodio in listEpisodiLink:
                episodiourl = "https://" + url.split("/")[2] + episodio.find("a")["href"]
                soap= self.__request(episodiourl)
                link = self.__findNewUrl(soap)
                if first:
                    findLinkFastList = self.__findUrlFastMode(link, len(listEpisodiLink))
                    if findLinkFastList is not None and len(findLinkFastList) == (len(listEpisodiLink) - start):
                        return findLinkFastList
                    first = False
                customPrint("Acquisito l'episodio " + str(self._AnimeWebSite__indexanime) + " di " + len(listEpisodi) + " : " + self.__getEpisodioNameFileFromUrl(link))
                listEpisodi.append(link)
            return listEpisodi
        else:
            return None

    def __checkIsAiring(self):
        for item in self.__soup.findAll("dd"):
            if "In corso" in item.text:
                self.airing = True

    def __findUrlFastMode(self, url: string, lentotalepisodi : int):
        from utility import customPrint
        episodeList = []
        indexAnime = self._AnimeWebSite__indexanime
        for e in url.split("_"):
            try:
                if int(e) == indexAnime:
                    startingepg = e
                break
            except ValueError:
                pass
        lenstartingepg = len(startingepg)
        for index in range(int(startingepg), lentotalepisodi+1):
            episodeNumber = str(index)
            indexlen = len(episodeNumber)
            if indexlen != lenstartingepg:
                for e in range(indexlen, lenstartingepg):
                    episodeNumber = "0" + episodeNumber
            url_download = url.replace(startingepg, episodeNumber)
            request = requests.head(url_download, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36'})
            if request.status_code == 200:
                customPrint("Acquisito l'episodio " + str(indexAnime) + " di " + str(
                    lentotalepisodi) + " : " + self.__getEpisodioNameFileFromUrl(url_download))
                episodeList.append(url_download)
                indexAnime +=1
            else:
                customPrint("Impossibile acquisire anime in modalità rapida, provo un altro modo")
                return None
        return episodeList

    def downloadAnime(self, link: string, start: int = 0, listEpisodi: array = None):
        from utility import bar_progress
        if listEpisodi is None and link is not None:
            listEpisodi = self.getEpisodeList(link, start)
        if listEpisodi is None:
            return None
        listAnimeDownloaded = []
        anime_name = self.name.replace(":", "").replace("\\", "").replace("/", "").replace(":", "").replace("*",
                                                                                                            "").replace(
            "?", "").replace("”", "").replace("<", "").replace(">", "").replace("|", "")
        dir = os.path.join(os.getcwd(), anime_name)
        if not os.path.exists(dir):
            os.mkdir(dir)
        else:
            for file in os.listdir(dir):
                if file.endswith(".mp4"):
                    listAnimeDownloaded.append(file)
        airingurl = os.path.join(dir, ".url")
        if self.airing and os.path.exists(airingurl) == False:
            file = open(airingurl, 'w+')
            file.write(link)
            file.close()
        incomplete = os.path.join(dir, ".incomplete")
        if os.path.exists(incomplete) == False:
            file = open(incomplete, 'w+')
            file.write(link)
            file.close()
        self.incomplete = True
        print("Scarico i " + str(len(listEpisodi)) + " episodi/o")
        i = 1
        for episodio in listEpisodi:
            splitEp = self.__getEpisodioNameFileFromUrl(episodio)
            print(str(i) + ". Avvio il download di: " + splitEp)
            if splitEp in listAnimeDownloaded:
                print(splitEp + " già trovato nei file scaricati")
            else:
                try:
                    wget.download(episodio, dir, bar=bar_progress)
                    print("")
                except Exception:
                    print("")
                    return False

            i += 1
        if os.path.exists(incomplete) == True:
            os.remove(incomplete)
        return True

    def __getEpisodioNameFileFromUrl(self,url: string):
        array = url.split("/")
        for word in array:
            if word.endswith(".mp4"):
                return word