from __future__ import annotations

from typing import List, Dict, Optional
import re
from bs4 import BeautifulSoup
import animeworld as aw
from tqdm import tqdm
from anime_season_resolver import AnimeSeasonResolver

from AnimeWebSite import AnimeWebSite


class AnimeWorld(AnimeWebSite):
    season_number = ""

    def __init__(self, url: str):
        self._anime: Optional[aw.Anime] = None
        super().__init__(url)

    def _parse_url(self) -> str:
        url = self.url.strip()
        m = re.match(r'^(https?://[^/]+)(/play/[^/]+)', url)
        if m:
            aw.SES.base_url = m.group(1)
            return m.group(2)
        return url

    def _get_best_link(self, episode) -> Optional[str]:
        if not hasattr(episode, 'links') or not episode.links:
            return None
        for lnk in episode.links:
            if 'animeworld' in getattr(lnk, 'name', '').lower():
                return lnk.link
        return episode.links[0].link

    def _name_from_url(self, url: str) -> str:
        filename = url.rstrip('/').split('/')[-1].split('?')[0]
        if not filename.lower().endswith('.mp4'):
            filename += '.mp4'
        return filename

    def _get_anilist_url_from_html(self, html: bytes) -> str | None:
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('a', id='anilist-button')
        if element and element.get('href'):
            return element['href']
        element = soup.find('a', attrs={'data-tippy-content': 'Scheda AniList'})
        if element and element.get('href'):
            return element['href']
        return ""

    def _get_mal_url_from_html(self, html: bytes) -> str | None:
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('a', id='mal-button')
        if element and element.get('href'):
            return element['href']
        element = soup.find('a', attrs={'data-tippy-content': 'Scheda MyAnimeList'})
        if element and element.get('href'):
            return element['href']
        return ""

    def _normalize_episode_name(self, name: str) -> str:
        if self.season_number == "" and "movie" not in name.lower():
            url_anilist = self._get_anilist_url_from_html(self._anime.html)
            url_mal = self._get_mal_url_from_html(self._anime.html)
            api = AnimeSeasonResolver()
            self.season_number = api.get_season(url_anilist, url_mal)
        if self.season_number:
            return re.sub(r'[_-]Ep[_-](\d+)', lambda m: f'_{self.season_number}EP{m.group(1)}', name)
        return name

    def getEpisodeList(self, start: int = -1) -> Optional[List[Dict]]:
        path = self._parse_url()

        try:
            self._anime = aw.Anime(link=path)
        except aw.Error404:
            print('Anime non trovato (404).')
            return None
        except aw.DeprecatedLibrary as e:
            print(f'Libreria deprecata: {e}')
            return None
        except Exception as e:
            print(f'Errore creazione anime: {e}')
            return None

        try:
            self.name = self._anime.getName()
        except Exception:
            slug = path.rstrip('/').split('/')[-1]
            self.name = re.sub(r'\.[A-Za-z0-9]{2,8}$', '', slug).replace('-', ' ').title()

        try:
            info = self._anime.getInfo()
            stato = str(info.get('Stato', '')).lower()
            self.airing = 'in corso' in stato or 'ongoing' in stato
        except Exception:
            self.airing = False

        try:
            episodes = list(self._anime.getEpisodes())
        except aw.AnimeNotAvailable as e:
            print(f'Anime non disponibile: {e}')
            return None
        except Exception as e:
            print(f'Errore recupero episodi: {e}')
            return None

        start_index = 0 if start == -1 else max(start, 0)
        episodes = episodes[start_index:]
        total = len(episodes)

        if total == 0:
            return []

        print(f'\nAnime:   {self.name}')
        print(f"In corso:  {'Sì' if self.airing else 'No'}")
        print(f'Episodi: {total}\n')

        final_list = []
        with tqdm(total=total, desc='Analisi episodi', unit='ep', dynamic_ncols=True) as pbar:
            for ep in episodes:
                link = self._get_best_link(ep)
                name = self._name_from_url(link) if link else f'Episodio_{ep.number}.mp4'
                name = self._normalize_episode_name(name)
                final_list.append({
                    'episode': ep,
                    'number': str(ep.number),
                    'name': name,
                    'url': link or '',
                })
                pbar.set_postfix_str(name[:50])
                pbar.update(1)

        for ep in final_list:
            tqdm.write(f"  [EP {ep['number']:>3}] {ep['name']}")

        return final_list

    def downloadAnime(self, start: int = -1, listEpisodi=None, max_workers: int = 6):
        result = super().downloadAnime(
            start=start,
            listEpisodi=listEpisodi,
            max_workers=max_workers,
        )
        if result is not True:
            raise Exception('Download fallito')
        return result