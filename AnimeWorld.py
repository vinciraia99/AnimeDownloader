import array
import os
import string
import urllib
from urllib import request

import wget
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.remote.webelement import WebElement


class AnimeWorld:

    def __init__(self, driver: webdriver):
        self.incomplete = False
        self.airing = False
        self.name = None
        self.driver = driver
        self.plyrControlListIndex = 18
        self.__latest = 0

    def __fixUrl(self, link: string):
        if "www.animeworld" in link:
            try:
                split = link.split("/")
                link_filter = split[0] + "/"
                for i in range(1, 5):
                    link_filter += "/" + split[i]
                return link_filter
            except Exception:
                return None
        else:
            return None

    def __findNewUrl(self, plyrControlList: array):
        if plyrControlList[self.plyrControlListIndex].get_attribute("href") is None:
            for i in range(0, len(plyrControlList)):
                if not plyrControlList[i].get_attribute("href") is None and ".mp4" in plyrControlList[i].get_attribute(
                        "href"):
                    self.plyrControlListIndex = i
                    return plyrControlList[i].get_attribute("href")
        elif ".mp4" in plyrControlList[self.plyrControlListIndex].get_attribute("href"):
            return plyrControlList[self.plyrControlListIndex].get_attribute("href")
        return None

    def __rangeEpisodeFindFromStartIndex(self, start: int, end: int, episode: int, episodiTab: list):
        if start == end:
            if int(episodiTab[start].text.split("-")[0]) <= episode <= int(episodiTab[start].text.split("-")[1]):
                return episodiTab[start:len(episodiTab)]
        else:
            for x in range(start, end):
                if int(episodiTab[x].text.split("-")[0]) <= episode <= int(episodiTab[x].text.split("-")[1]):
                    return episodiTab[x:len(episodiTab)]

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
                    return self.__rangeEpisodeFindFromStartIndex(0, int(len(episodiTab) / 2), start, episodiTab)
                elif start > half:
                    return self.__rangeEpisodeFindFromStartIndex(int(len(episodiTab) / 2), int(len(episodiTab)), start,
                                                                 episodiTab)
                elif start == half:
                    return self.__rangeEpisodeFindFromStartIndex(int(len(episodiTab) / 2), int(len(episodiTab) / 2),
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

    def __checkUrl(self, link: string, index: int) -> bool:
        if index < 10:
            index = "0" + str(index)
        else:
            index = str(index)
        for e in link.split("_"):
            if index == e:
                return True
        return False

    def getEpisodeList(self, link: string, start: int = 0) -> array:
        from utility import customPrint
        url = self.__fixUrl(link)
        if url is not None:
            self.driver.get(url)
            self.name = self.__getAnimeName()
            if self.name is None:
                return None
            self.__checkIsAiring()
            customPrint("Acquisisco gli episodi per l'anime: " + self.name)
            listLargeEpisode = self.__largeEpisodeFetch(start)
            listEpisodi = []
            if len(listLargeEpisode) == 0:
                return self.__getEpisodeTab(0, listEpisodi, listLargeEpisode, start)
            else:
                for episodeTab in range(0, len(listLargeEpisode)):
                    return self.__getEpisodeTab(episodeTab, listEpisodi, listLargeEpisode, start)
        else:
            return None

    def __checkIsAiring(self):
        for item in self.driver.find_elements(by=By.CSS_SELECTOR, value="dd"):
            if "In Corso" in item.text:
                self.airing = True

    def __getEpisodeTab(self, episodeTab, listEpisodi, listLargeEpisode, start) -> array:
        from utility import customPrint
        i = start + 1
        if len(listLargeEpisode) > 0:
            lentotalepisodi = listLargeEpisode[len(listLargeEpisode) - 1].text.split("-")[1]
            if start != 0 and episodeTab != 0:
                start = start - listLargeEpisode[episodeTab].text.split("-")[1]
        if len(listLargeEpisode) != 0:
            self.__ceckActionChain(listLargeEpisode[episodeTab], "span.rangetitle.active")
        servertab = self.driver.find_element(by=By.CSS_SELECTOR, value="div.server.active")
        episoditab = servertab.find_element(by=By.CSS_SELECTOR, value=".episodes.range.active")
        episodi = episoditab.find_elements(by=By.CLASS_NAME, value="episode")
        lenepisodi = len(episodi)
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
                        EC.visibility_of_element_located((By.CLASS_NAME, "plyr__control")))
                    new_url_download = self.__findNewUrl(
                        self.driver.find_elements(by=By.CLASS_NAME, value="plyr__control"))
                    try:
                        if self.__checkUrl(new_url_download, i):
                            customPrint("Acquisito l'episodio " + str(i) + " di " + str(lentotalepisodi) + " : " +
                                        new_url_download.split("filename=")[1])
                            listEpisodi.append(new_url_download)
                            i += 1
                            break
                    except IndexError:
                        raise Exception("AnimeUnity non ha disponibile per il download l'anime")
                except TimeoutException:
                    tentativi += 1
                    continue
        return listEpisodi

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

    def __downloadWithUrl2(self, dir, splitEp, anime_name):
        print("Download fallito, provo con un'altro server")
        downloaded = False
        if self.__latest != 0:
            downloaded = self.__download(dir, self.__latest, splitEp, anime_name)
        if not downloaded:
            for i in range(0, 100):
                if i != self.__latest:
                    downloaded = self.__download(dir, i, splitEp, anime_name)
                    if downloaded:
                        break
        self.__latest = i
        os.rename(os.path.join(dir, splitEp + ".tmp"), os.path.join(dir, splitEp))
        print("")
        return downloaded

    def __downloadWithUrl(self, dir, splitEp, url, anime_name):
        from utility import show_progress
        print("Download fallito, provo con un'altro server")
        for i in range(0, 50):
            try:
                episodio_url = url + splitEp.split("_")[0] + "/" + splitEp
                request.urlretrieve(episodio_url, os.path.join(dir, splitEp + ".tmp"), show_progress)
            except urllib.error.HTTPError:
                if "ITA" in anime_name:
                    episodio_url = url + splitEp.split("_")[0] + "ITA" + "/" + splitEp
                request.urlretrieve(episodio_url, os.path.join(dir, splitEp + ".tmp"), show_progress)
        os.rename(os.path.join(dir, splitEp + ".tmp"), os.path.join(dir, splitEp))
        print("")

    def __download(dir, index, splitEp, anime_name):
        from utility import show_progress
        url = "https://server" + str(index) + ".streamingaw.online/DDL/ANIME/"
        try:
            episodio_url = url + splitEp.split("_")[0] + "/" + splitEp
            test = request.urlretrieve(episodio_url, os.path.join(dir, splitEp + ".tmp"), show_progress)
            if not test is None:
                return True
        except (urllib.error.HTTPError, urllib.error.URLError):
            try:
                if "ITA" in anime_name:
                    episodio_url = url + splitEp.split("_")[0] + "ITA" + "/" + splitEp
                    test = request.urlretrieve(episodio_url, os.path.join(dir, splitEp + ".tmp"), show_progress)
                    if not test is None:
                        return True
            except(urllib.error.HTTPError, urllib.error.URLError):
                return False
        return False
