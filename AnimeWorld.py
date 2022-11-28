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
            href= link.get_attribute('href')
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
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(0, int(len(episodiTab) / 2), start, episodiTab)
                elif start > half:
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(int(len(episodiTab) / 2), int(len(episodiTab)), start,
                                                                 episodiTab)
                elif start == half:
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(int(len(episodiTab) / 2), int(len(episodiTab) / 2),
                                                                 start,
                                                                 episodiTab)
            return episodiTab
        else:
            return episode_nav

    def __ceckActionChain(self, e: WebElement, value: string):
        ActionChains(self.driver).move_to_element(e).click().perform()
        while True:
            for e in self.driver.find_elements(by=By.CSS_SELECTOR, value=value):
                if len(e.text)>0:
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
                listEpisodi+= self.__getEpisodeTab(0, listLargeEpisode, start)
            else:
                listEpisodi += self.__getEpisodeTab(0, listLargeEpisode, start)
                for episodeTab in range(1, len(listLargeEpisode)):
                    listEpisodi += self.__getEpisodeTab(episodeTab, listLargeEpisode, 0)
        else:
            return None

    def __checkIsAiring(self):
        for item in self.driver.find_elements(by=By.CSS_SELECTOR, value="dd"):
            if "In Corso" in item.text:
                self.airing = True

    def __getTotalEpisode(self,lentotalepisodi : int):
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
                start = start - int(listLargeEpisode[episodeTab].text.replace(" ","").split("-")[0])
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
                    raise Exception("Animeunity non risponde correttamente")
                try:
                    self.__ceckActionChain(episodi[x], "a.active")
                    self.driver.execute_script(
                        "try{document.getElementsByTagName(\"iframe\")[0].remove()}catch(err){}")
                    WebDriverWait(self.driver, 1).until(
                        EC.visibility_of_element_located((By.ID, "alternativeDownloadLink")))
                    new_url_download = self.__findNewUrl()
                    try:
                        if self._AnimeWebSite__checkUrl(new_url_download, self._AnimeWebSite__indexanime,self.__getTotalEpisode(lentotalepisodi),episodi[x]):
                            customPrint("Acquisito l'episodio " + str( self._AnimeWebSite__indexanime) + " di " + str(lentotalepisodi) + " : " + new_url_download)
                            listEpisodi.append(new_url_download)
                            self._AnimeWebSite__indexanime += 1
                            break
                    except IndexError:
                        raise Exception("AnimeWorld non ha disponibile per il download l'anime")
                except TimeoutException:
                    tentativi += 1
                    continue
        return listEpisodi

    #TODO Da implementare
    def __findUrlFastMode(self,url :string,start,lentotalepisodi):
        for e in url.split("_"):
            try:
                int(e)
            except ValueError:
                pass
        request = requests.get('http://www.example.com')
        if request.status_code == 200:
            print('Web site exists')
        else:
            print('Web site does not exist')


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
        print("Scarico i " + str(len(listEpisodi)) + " episodi/o")
        i = 1
        incomplete = os.path.join(dir, ".incomplete")
        if os.path.exists(incomplete) == False:
            file = open(incomplete, 'w+')
            file.write(link)
            file.close()
        self.incomplete = True
        for episodio in listEpisodi:
            splitEp = episodio.split("filename=")[1]
            print(str(i) + ". Avvio il download di: " + splitEp)
            if splitEp in listAnimeDownloaded:
                print(splitEp + " già trovato nei file scaricati")
            else:
                try:
                    wget.download(episodio, dir, bar=bar_progress)
                    print("")
                except Exception:
                    if not self.__downloadWithUrl2(dir, splitEp, anime_name):
                        try:
                            print("")
                            url = "http://www.dororo-anime.eu/DLL/ANIME/"
                            self.__downloadWithUrl(dir, splitEp, url, anime_name)
                        except Exception:
                            print("")
                            return False

            i += 1
        if os.path.exists(incomplete) == True:
            os.remove(incomplete)
        return True