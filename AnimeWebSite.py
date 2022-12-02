import array
import string

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement


class AnimeWebSite:

    def __init__(self, driver: webdriver):
        self.incomplete = False
        self.airing = False
        self.name = None
        self.driver = driver
        self.plyrControlListIndex = 18
        self.__indexanime = 1

    def __fixUrl(self, link: string, website: str):
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

    def __checkUrl(self, link: string, index: int,lenepisodi : int, episodio : WebElement) -> bool:
        flag = False
        if index > 10:
            flag = True
        for e in link.split("_"):
            try:
                if int(e) > lenepisodi:
                    index = (int(index) + lenepisodi)-1
                elif int(e) == lenepisodi and index == 1:
                    index = lenepisodi
                if index == int(e):
                    return True
                elif flag and "0" + str(index) == e:
                    return True
                elif len(e.split("-"))>0 and episodio.text.replace(" ","") == e:
                    self.__indexanime = int(episodio.text.split("-")[1])
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
