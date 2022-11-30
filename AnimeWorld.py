import array
import os
import string
import urllib
from urllib import request

import requests
import wget
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement

from AnimeWebSite import AnimeWebSite


class AnimeWorld(AnimeWebSite):

    def __findNewUrl(self):
        parent = self.driver.find_element(by=By.CLASS_NAME, value="downloads")
        listLink = parent.find_elements(by=By.CSS_SELECTOR, value="a")
        for link in listLink:
            href = link.get_attribute('href')
            if ".mp4" in href and not ".php" in href:
                return href

    def __largeEpisodeFetch(self, start: int) -> array:
        episode_nav = self.driver.find_elements(by=By.CLASS_NAME, value="rangetitle")
        if len(episode_nav) > 0:
            servertabfinder = self.driver.find_elements(by=By.CLASS_NAME, value="server-tab")
            for server in servertabfinder:
                if "AnimeWorld" in server.text:
                    id = server.get_attribute('data-name')
                    break
            serverfinder = self.driver.find_elements(by=By.CLASS_NAME, value="server")
            for server in serverfinder:
                if str(id) == server.get_attribute('data-name'):
                    parent = server
                    break
            episodiTab = parent.find_elements(by=By.CLASS_NAME, value="rangetitle")
            if start != 0:
                half = int(episodiTab[int(len(episodiTab) / 2)].text.split("-")[0])
                if start < half:
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(0, int(len(episodiTab) / 2), start,
                                                                              episodiTab)
                elif start > half:
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(int(len(episodiTab) / 2),
                                                                              int(len(episodiTab)), start,
                                                                              episodiTab)
                elif start == half:
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(int(len(episodiTab) / 2),
                                                                              int(len(episodiTab) / 2),
                                                                              start,
                                                                              episodiTab)
            return episodiTab
        else:
            return episode_nav

    def __ceckActionChain(self, e: WebElement, value: string):
        ActionChains(self.driver).move_to_element(e).click().perform()
        while True:
            for e in self.driver.find_elements(by=By.CSS_SELECTOR, value=value):
                if len(e.text) > 0:
                    element = e
                    break
            try:
                while e.text != element.text:
                    ActionChains(self.driver).move_to_element(e).click().perform()
                break
            except (StaleElementReferenceException, NoSuchElementException):
                pass

    def __getAnimeName(self) -> string:
        try:
            WebDriverWait(self.driver, 1).until(EC.visibility_of_element_located((By.ID, "anime-title")))
            return self.driver.find_element(by=By.ID, value="anime-title").accessible_name
        except TimeoutException:
            return None

    def getEpisodeList(self, link: string, start: int = 0) -> array:
        from utility import customPrint
        url = self._AnimeWebSite__fixUrl(link, "www.animeworld")
        if url is not None:
            self.driver.get(url)
            self.name = self.__getAnimeName()
            if self.name is None:
                return None
            self.__checkIsAiring()
            customPrint("Acquisisco gli episodi per l'anime: " + self.name)
            listLargeEpisode = self.__largeEpisodeFetch(start)
            listEpisodi = []
            if start != 0:
                self._AnimeWebSite__indexanime = start
            if len(listLargeEpisode) == 0:
                listEpisodi += self.__getEpisodeTab(0, listLargeEpisode, start)
            else:
                listEpisodi += self.__getEpisodeTab(0, listLargeEpisode, start)
                if len(listEpisodi) == 50-(start-1):
                   for episodeTab in range(1, len(listLargeEpisode)):
                    listEpisodi += self.__getEpisodeTab(episodeTab, listLargeEpisode, 0)
            return listEpisodi
        else:
            return None

    def __checkIsAiring(self):
        for item in self.driver.find_elements(by=By.CSS_SELECTOR, value="dd"):
            if "In corso" in item.text:
                self.airing = True

    def __getTotalEpisode(self, lentotalepisodi: int):
        for item in self.driver.find_elements(by=By.CSS_SELECTOR, value="dd"):
            if "??" in item.text:
                return int(lentotalepisodi)
            try:
                e = int(item.text)
                return e
            except ValueError:
                pass

    def __getEpisodeTab(self, episodeTab, listLargeEpisode, start) -> array:
        from utility import customPrint
        if len(listLargeEpisode) > 0:
            lentotalepisodi = listLargeEpisode[len(listLargeEpisode) - 1].text.split("-")[1]
            if start != 0:
                start = start - int(listLargeEpisode[episodeTab].text.replace(" ", "").split("-")[0])
        if len(listLargeEpisode) != 0:
            self.__ceckActionChain(listLargeEpisode[episodeTab], "span.rangetitle.active")
        servertab = self.driver.find_element(by=By.CSS_SELECTOR, value="div.server.active")
        episoditab = servertab.find_element(by=By.CSS_SELECTOR, value=".episodes.range.active")
        episodi = episoditab.find_elements(by=By.CLASS_NAME, value="episode")
        lenepisodi = len(episodi)
        listEpisodi = []
        if len(listLargeEpisode) == 0:
            lentotalepisodi = len(episodi)
        for x in range(start, lenepisodi):
            tentativi = 0
            while True:
                if tentativi > 100:
                    raise Exception(self.__class__.__name__ + " non risponde correttamente")
                try:
                    self.__ceckActionChain(episodi[x], "a.active")
                    #self.driver.execute_script("try{document.getElementsByTagName(\"iframe\")[0].remove()}catch(err){}")
                    WebDriverWait(self.driver, 1).until(
                        EC.visibility_of_element_located((By.ID, "alternativeDownloadLink")))
                    new_url_download = self.__findNewUrl()
                    try:
                        if self._AnimeWebSite__checkUrl(new_url_download, self._AnimeWebSite__indexanime,
                                                        self.__getTotalEpisode(lentotalepisodi), episodi[x]):
                            if self._AnimeWebSite__indexanime == start +1:
                                findLinkFastList = self.__findUrlFastMode(new_url_download, int(lentotalepisodi))
                                if findLinkFastList is not None and len(findLinkFastList) == (int(lentotalepisodi) - start):
                                    return findLinkFastList
                            customPrint("Acquisito l'episodio " + str(self._AnimeWebSite__indexanime) + " di " + str(
                                lentotalepisodi) + " : " + self.__getEpisodioNameFileFromUrl(new_url_download))
                            listEpisodi.append(new_url_download)
                            self._AnimeWebSite__indexanime += 1
                            break
                    except IndexError:
                        raise Exception(self.__class__.__name__ + " non ha disponibile per il download l'anime")
                except TimeoutException:
                    tentativi += 1
                    continue
        return listEpisodi
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