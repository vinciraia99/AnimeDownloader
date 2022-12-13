import array
import os
import string
import urllib
from urllib import request

from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from AnimeWebSite import AnimeWebSite


class AnimeUnity(AnimeWebSite):
    driver = None

    def __init__(self, url: string):
        super(AnimeUnity, self).__init__(url)
        self.__latest = 0
        self.plyrControlListIndex = 18
        if AnimeUnity.driver is None:
            from utility import initDriver
            AnimeUnity.driver = initDriver()

    def __largeEpisodeFetch(self, start: int) -> array:
        episode_nav = AnimeUnity.driver.find_elements(by=By.ID, value="episode-nav")
        if len(episode_nav) > 0:
            episodiTab = AnimeUnity.driver.find_elements(by=By.CLASS_NAME, value="btn-episode-nav")
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
                                                                              int(len(episodiTab) / 2), start,
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
        ActionChains(AnimeUnity.driver).move_to_element(e).click().perform()
        while True:
            try:
                while e.text != AnimeUnity.driver.find_element(by=By.CSS_SELECTOR, value=value).text:
                    ActionChains(AnimeUnity.driver).move_to_element(e).click().perform()
                break
            except (StaleElementReferenceException, NoSuchElementException):
                pass

    def __getAnimeName(self) -> string:
        try:
            WebDriverWait(AnimeUnity.driver, 1).until(EC.visibility_of_element_located((By.CLASS_NAME, "title")))
            return AnimeUnity.driver.find_element(by=By.CLASS_NAME, value="title").accessible_name
        except TimeoutException:
            return None

    def getEpisodeList(self, start: int = 0) -> array:
        url = self._AnimeWebSite__fixUrl(self.url, "www.animeunity")
        if url is not None:
            AnimeUnity.driver.get(url)
            self.name = self.__getAnimeName()
            if self.name is None:
                return None
            self.__checkIsAiring()
            from utility import customPrint
            customPrint("Acquisisco gli episodi per l'anime: " + self.name)
            listLargeEpisode = self.__largeEpisodeFetch(start)
            listEpisodi = []
            if start != 0:
                self._AnimeWebSite__indexanime = start + 1
            if len(listLargeEpisode) == 0:
                result = self.__getEpisodeTab(0, listLargeEpisode, start)
            else:
                listEpisodi += self.__getEpisodeTab(0, listLargeEpisode, start)
                for episodeTab in range(1, len(listLargeEpisode)):
                    listEpisodi += self.__getEpisodeTab(episodeTab, listLargeEpisode, 0)
                result = listEpisodi
        else:
            result = None
        if result is not None:
            listDictEpisodi = []
            for episodio in result:
                dict = {
                    'url': episodio,
                    'name': self.__getEpisodioNameFileFromUrl(episodio)
                }
                listDictEpisodi.append(dict)
            return listDictEpisodi
        return result

    def __checkIsAiring(self):
        for item in AnimeUnity.driver.find_elements(by=By.CLASS_NAME, value="info-item"):
            if "In Corso" in item.text:
                self.airing = True

    def __getTotalEpisode(self, lentotalepisodi: int):
        for item in AnimeUnity.driver.find_elements(by=By.CLASS_NAME, value="info-item"):
            try:
                e = int(item.text.replace("Episodi\n", ""))
                return e
            except ValueError:
                pass
        return lentotalepisodi

    def __getEpisodeTab(self, episodeTab, listLargeEpisode, start) -> array:
        listEpisodi = []
        if len(listLargeEpisode) > 0:
            lentotalepisodi = listLargeEpisode[len(listLargeEpisode) - 1].text.split("-")[1]
            if start != 0:
                start = start - int(listLargeEpisode[episodeTab].text.split("-")[0])
        if len(listLargeEpisode) != 0:
            self.__ceckActionChain(listLargeEpisode[episodeTab], ".btn-episode-nav.active")
        WebDriverWait(AnimeUnity.driver, 5).until(EC.visibility_of_element_located((By.CLASS_NAME, "episode-item")))
        episodi = AnimeUnity.driver.find_elements(by=By.CLASS_NAME, value="episode-item")
        lenepisodi = len(episodi)
        printendIndex = self._AnimeWebSite__indexanime
        if len(listLargeEpisode) == 0:
            lentotalepisodi = len(episodi)
        for x in range(start, lenepisodi):
            tentativi = 0
            while True:
                if tentativi > 100:
                    raise Exception("Animeunity non risponde correttamente")
                try:
                    self.__ceckActionChain(episodi[x], ".episode-item.active")
                    AnimeUnity.driver.execute_script(
                        "try{document.getElementsByTagName(\"iframe\")[0].remove()}catch(err){}")
                    WebDriverWait(AnimeUnity.driver, 1).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, "plyr__control")))
                    new_url_download = self.__findNewUrl(
                        AnimeUnity.driver.find_elements(by=By.CLASS_NAME, value="plyr__control"))
                    if x == 0:
                        for e in new_url_download.split("_"):
                            try:
                                if int(e) == 0:
                                    self._AnimeWebSite__indexanime = 0
                                    break
                            except ValueError:
                                pass
                    try:
                        if self.__checkUrl(new_url_download,
                                           self.__getTotalEpisode(int(lentotalepisodi)), episodi[x]):
                            print("Acquisito l'episodio " + str(printendIndex) + " di " + str(
                                lentotalepisodi) + " : " +
                                  self.__getEpisodioNameFileFromUrl(new_url_download))
                            listEpisodi.append(new_url_download)
                            self._AnimeWebSite__indexanime += 1
                            printendIndex += 1
                            break
                    except IndexError:
                        raise Exception("AnimeUnity non ha disponibile per il download l'anime")
                except TimeoutException:
                    tentativi += 1
                    continue
        return listEpisodi

    def __getEpisodioNameFileFromUrl(self, url):
        return url.split("filename=")[1]

    def downloadAnime(self, start: int = 0, listEpisodi: array = None):
        listEpisodi = super().downloadAnime(start, listEpisodi)
        if listEpisodi != True:
            anime_name = self._AnimeWebSite__replaceNameDir()
            for episodio in listEpisodi:
                dir = self._AnimeWebSite__createOrCheckDowloadedFileDir(anime_name)
                if not self.__downloadWithUrl2(dir, episodio["name"], anime_name):
                    try:
                        print("")
                        url = "http://www.dororo-anime.eu/DLL/ANIME/"
                        self.__downloadWithUrl(dir, episodio["url"], url, anime_name)
                    except Exception:
                        print("")
                        return False
        self._AnimeWebSite__removeIncompleteFile(self._AnimeWebSite__incomplete)
        return listEpisodi

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
        from utility import progressBar
        print("Download fallito, provo con un'altro server")
        for i in range(0, 50):
            try:
                episodio_url = url + splitEp.split("_")[0] + "/" + splitEp
                request.urlretrieve(episodio_url, os.path.join(dir, splitEp + ".tmp"), progressBar)
            except urllib.error.HTTPError:
                if "ITA" in anime_name:
                    episodio_url = url + splitEp.split("_")[0] + "ITA" + "/" + splitEp
                request.urlretrieve(episodio_url, os.path.join(dir, splitEp + ".tmp"), progressBar)
        os.rename(os.path.join(dir, splitEp + ".tmp"), os.path.join(dir, splitEp))
        print("")

    def __download(self, directory, index, splitEp, anime_name):
        from utility import progressBar
        url = "https://server" + str(index) + ".streamingaw.online/DDL/ANIME/"
        try:
            episodio_url = url + splitEp.split("_")[0] + "/" + splitEp
            test = request.urlretrieve(episodio_url, os.path.join(directory, splitEp + ".tmp"), progressBar)
            if not test is None:
                return True
        except (urllib.error.HTTPError, urllib.error.URLError):
            try:
                if "ITA" in anime_name:
                    episodio_url = url + splitEp.split("_")[0] + "ITA" + "/" + splitEp
                    test = request.urlretrieve(episodio_url, os.path.join(directory, splitEp + ".tmp"), progressBar)
                    if not test is None:
                        return True
            except(urllib.error.HTTPError, urllib.error.URLError):
                return False
        return False

    def __checkUrl(self, link: string, lenepisodi: int, episodio: WebElement) -> bool:
        index = self._AnimeWebSite__indexanime
        flag = False
        if index > 10:
            flag = True
        if "Movie" in link:
            return True
        for e in link.split("_"):
            try:
                if int(e) > lenepisodi:
                    index = (int(index) + lenepisodi) - 1
                elif int(e) == lenepisodi and index == 1:
                    index = lenepisodi
                if index == int(e):
                    return True
                elif flag and "0" + str(index) == e:
                    return True
                elif len(e.split("-")) > 0 and episodio.text.replace(" ", "") == e:
                    self._AnimeWebSite__indexanime = int(episodio.text.split("-")[1])
                    return True
            except ValueError:
                pass
        return False

    def __rangeEpisodeFindFromStartIndex(self, start: int, end: int, episode: int, episodiTab: list):
        if start == end:
            if int(episodiTab[start].text.split("-")[0]) <= episode <= int(episodiTab[start].text.split("-")[1]):
                return episodiTab[start:len(episodiTab)]
        else:
            for x in range(start, end):
                if int(episodiTab[x].text.split("-")[0]) <= episode <= int(episodiTab[x].text.split("-")[1]):
                    return episodiTab[x:len(episodiTab)]
