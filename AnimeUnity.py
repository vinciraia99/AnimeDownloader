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
from AnimeWebSite import AnimeWebSite


class AnimeUnity(AnimeWebSite):

    def __init__(self, driver: webdriver):
        super(AnimeUnity, self).__init__(driver)
        self.__latest=0

    def __largeEpisodeFetch(self, start: int) -> array:
        episode_nav = self.driver.find_elements(by=By.ID, value="episode-nav")
        if len(episode_nav) >0 :
            episodiTab = self.driver.find_elements(by=By.CLASS_NAME, value="btn-episode-nav")
            if start != 0:
                half = int(episodiTab[int(len(episodiTab) / 2)].text.split("-")[0])
                if start < half:
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(0, int(len(episodiTab) / 2), start, episodiTab)
                elif start > half:
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(int(len(episodiTab) / 2), int(len(episodiTab)), start,
                                                                episodiTab)
                elif start == half:
                    return self._AnimeWebSite__rangeEpisodeFindFromStartIndex(int(len(episodiTab) / 2), int(len(episodiTab) / 2), start,
                                                                episodiTab)
            return episodiTab
        else:
            return episode_nav

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

    def __ceckActionChain(self, e: WebElement, value: string):
        ActionChains(self.driver).move_to_element(e).click().perform()
        while True:
            try:
                while e.text != self.driver.find_element(by=By.CSS_SELECTOR, value=value).text:
                    ActionChains(self.driver).move_to_element(e).click().perform()
                break
            except (StaleElementReferenceException, NoSuchElementException):
                pass

    def __getAnimeName(self) -> string:
        try:
            WebDriverWait(self.driver, 1).until(EC.visibility_of_element_located((By.CLASS_NAME, "title")))
            return self.driver.find_element(by=By.CLASS_NAME, value="title").accessible_name
        except TimeoutException:
            return None

    def getEpisodeList(self, link: string, start: int = 0) -> array:
        from utility import customPrint
        url = self._AnimeWebSite__fixUrl(link,"www.animeunity")
        if url is not None:
            self.driver.get(url)
            self.name = self.__getAnimeName()
            if self.name is None:
                return None
            for item in self.driver.find_elements(by=By.CLASS_NAME, value="info-item"):
                if "In Corso" in item.text:
                    self.airing = True
            customPrint("Acquisisco gli episodi per l'anime: " + self.name)
            listLargeEpisode = self.__largeEpisodeFetch(start)
            listEpisodi = []
            if start != 0:
                self._AnimeWebSite__indexanime = start
            if len(listLargeEpisode) == 0:
                return self.__getEpisodeTab(0, listLargeEpisode, start)
            else:
                listEpisodi += self.__getEpisodeTab(0, listLargeEpisode, start)
                for episodeTab in range(1, len(listLargeEpisode)):
                    listEpisodi += self.__getEpisodeTab(episodeTab, listLargeEpisode, 0)
                return listEpisodi
        else:
            return None

    def __getTotalEpisode(self):
        for item in self.driver.find_elements(by=By.CLASS_NAME, value="info-item"):
            try:
                e = int(item.text.replace("Episodi\n",""))
                return e
            except ValueError:
                pass


    def __getEpisodeTab(self, episodeTab, listLargeEpisode, start) -> array:
        from utility import customPrint
        listEpisodi = []
        if len(listLargeEpisode) > 0:
            lentotalepisodi = listLargeEpisode[len(listLargeEpisode) - 1].text.split("-")[1]
            if start != 0:
                start = start - int(listLargeEpisode[episodeTab].text.split("-")[0])
        if len(listLargeEpisode) != 0:
            self.__ceckActionChain(listLargeEpisode[episodeTab], ".btn-episode-nav.active")
        WebDriverWait(self.driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "episode-item")))
        episodi = self.driver.find_elements(by=By.CLASS_NAME, value="episode-item")
        lenepisodi = len(episodi)
        if len(listLargeEpisode) == 0:
            lentotalepisodi = len(episodi)
        for x in range(start, lenepisodi):
            tentativi = 0
            while True:
                if tentativi > 100:
                    raise Exception("Animeunity non risponde correttamente")
                try:
                    self.__ceckActionChain(episodi[x], ".episode-item.active")
                    self.driver.execute_script(
                        "try{document.getElementsByTagName(\"iframe\")[0].remove()}catch(err){}")
                    WebDriverWait(self.driver, 1).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, "plyr__control")))
                    new_url_download = self.__findNewUrl(
                        self.driver.find_elements(by=By.CLASS_NAME, value="plyr__control"))
                    try:
                        if self._AnimeWebSite__checkUrl(new_url_download,  self._AnimeWebSite__indexanime,self.__getTotalEpisode(),episodi[x]):
                            customPrint("Acquisito l'episodio " + str( self._AnimeWebSite__indexanime) + " di " + str(lentotalepisodi) + " : " +
                                        new_url_download.split("filename=")[1])
                            listEpisodi.append(new_url_download)
                            self._AnimeWebSite__indexanime += 1
                            break
                    except IndexError:
                        raise Exception("AnimeUnity non ha disponibile per il download l'anime")
                except TimeoutException:
                    tentativi += 1
                    continue
        return listEpisodi

    def downloadAnime(self,link: string, start: int = 0, listEpisodi: array = None):
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
        if self._AnimeWebSite__latest != 0:
            downloaded = self.__download(dir, self._AnimeWebSite__latest, splitEp, anime_name)
        if not downloaded:
            for i in range(0, 100):
                if i != self._AnimeWebSite__latest:
                    downloaded = self.__download(dir, i, splitEp, anime_name)
                    if downloaded:
                        break
        self._AnimeWebSite__latest = i
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
