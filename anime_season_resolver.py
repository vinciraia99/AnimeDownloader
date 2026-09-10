import re
import time
import random
from curl_cffi import requests as curl_requests
import requests


class RateLimiter:
    def __init__(self, max_calls: int, period: float):
        self._max_calls = max_calls
        self._period = period
        self._calls: list[float] = []

    def wait(self):
        now = time.monotonic()
        self._calls = [t for t in self._calls if now - t < self._period]
        if len(self._calls) >= self._max_calls:
            sleep_for = self._period - (now - self._calls[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
        self._calls.append(time.monotonic())


def request_with_retry_cf(method_name: str, url: str, *, max_retries: int = 5, headers=None, **kwargs):
    last_exc = None
    for attempt in range(max_retries):
        try:
            func = getattr(curl_requests, method_name)
            resp = func(
                url,
                headers=headers,
                impersonate="chrome",
                timeout=15,
                **kwargs,
            )

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 30))
                time.sleep(retry_after + random.uniform(0.5, 1.5))
                continue

            if resp.status_code in (403, 500, 502, 503, 504):
                backoff = min(2 ** attempt, 30) + random.uniform(0, 1)
                time.sleep(backoff)
                continue

            resp.raise_for_status()
            return resp

        except Exception as exc:
            last_exc = exc
            if attempt == max_retries - 1:
                raise
            time.sleep(min(2 ** attempt, 30))

    raise Exception(f"Numero massimo di retry superato per {url}") from last_exc


class AniListAPI:
    def __init__(self):
        self._url = "https://graphql.anilist.co"
        self._headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://anilist.co",
            "Referer": "https://anilist.co/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        self._cache: dict[int, dict] = {}
        self._limiter = RateLimiter(max_calls=25, period=60)  # margine sotto i 30/min in stato degradato

    def _extract_anime_id(self, url: str) -> int:
        if url.isdigit():
            return int(url)

        match = re.search(r"anilist\.co/anime/(\d+)", url)
        if match:
            return int(match.group(1))

        raise ValueError(f"ID AniList non trovato in: {url}")

    def _post(self, query: str, variables: dict) -> dict:
        self._limiter.wait()
        response = request_with_retry_cf(
            "post",
            self._url,
            json={"query": query, "variables": variables},
            headers=self._headers,
        )

        data = response.json()
        if not isinstance(data, dict):
            raise Exception("Risposta AniList non valida")

        if data.get("errors"):
            raise Exception(f"Errore AniList: {data['errors']}")

        return data

    def _get_anime_info(self, anime_id: int) -> dict:
        if anime_id in self._cache:
            return self._cache[anime_id]

        query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                id
                format
                episodes
                title {
                    romaji
                    english
                    native
                }
                synonyms
                relations {
                    edges {
                        relationType
                        node {
                            id
                            format
                            episodes
                            title {
                                romaji
                                english
                                native
                            }
                        }
                    }
                }
            }
        }
        """

        data = self._post(query, {"id": anime_id})
        payload = data.get("data") or {}
        media = payload.get("Media")

        if not isinstance(media, dict):
            raise Exception(f"Anime con ID {anime_id} non trovato")

        self._cache[anime_id] = media
        return media

    def _normalize_title(self, title: str) -> str:
        if not title:
            return ""

        title = title.strip()
        title = re.sub(r"\s+", " ", title)
        return title.strip()

    def _preferred_title_from_media(self, media: dict) -> str:
        title_data = media.get("title") or {}
        return (
            title_data.get("romaji")
            or title_data.get("english")
            or title_data.get("native")
            or ""
        )

    def _preferred_title_from_node(self, node: dict) -> str:
        title_data = node.get("title") or {}
        return (
            title_data.get("romaji")
            or title_data.get("english")
            or title_data.get("native")
            or ""
        )

    def _roman_to_int(self, token: str) -> int | None:
        roman_map = {
            "ii": 2, "iii": 3, "iv": 4, "v": 5,
            "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
        }
        return roman_map.get(token.lower())

    def _extract_season_number_from_text(self, title: str) -> int | None:
        if not title:
            return None

        clean_title = self._normalize_title(title)

        numeric_patterns = [
            r"\bseason\s*(\d+)\b",
            r"\b(\d+)(?:st|nd|rd|th)\s*season\b",
            r"\bs(?:eason)?\s*(\d{1,2})\b",
        ]

        for pattern in numeric_patterns:
            match = re.search(pattern, clean_title, re.IGNORECASE)
            if match:
                return int(match.group(1))

        ordinal_words = {
            "second season": 2,
            "third season": 3,
            "fourth season": 4,
            "fifth season": 5,
            "sixth season": 6,
        }

        lowered = clean_title.lower()
        for key, value in ordinal_words.items():
            if key in lowered:
                return value

        roman_match = re.search(r"\b(ii|iii|iv|v|vi|vii|viii|ix|x)\b", clean_title, re.IGNORECASE)
        if roman_match:
            return self._roman_to_int(roman_match.group(1))

        return None

    def _extract_explicit_season(self, anime_id: int) -> int | None:
        info = self._get_anime_info(anime_id)
        title_data = info.get("title") or {}
        synonyms = info.get("synonyms") or []

        titles = [
            title_data.get("romaji") or "",
            title_data.get("english") or "",
            title_data.get("native") or "",
        ]

        for synonym in synonyms:
            if isinstance(synonym, str):
                titles.append(synonym)

        for title in titles:
            season = self._extract_season_number_from_text(title)
            if season is not None:
                return season

        return None

    def _looks_like_non_season_entry(self, title: str, fmt: str | None) -> bool:
        normalized = self._normalize_title(title).lower()
        fmt = (fmt or "").upper()

        if fmt in {"MOVIE", "SPECIAL", "OVA", "ONA", "MUSIC"}:
            return True

        patterns = [
            r"\bmovie\b", r"\bspecial\b", r"\bova\b", r"\bona\b",
            r"\brecap\b", r"\bsummary\b", r"\bedition\b", r"\bpilot\b",
            r"\bshorts?\b", r"\bcm\b", r"\bpv\b", r"\bpromo\b",
            r"\bpromotional\b", r"\bpreview\b",
        ]

        return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns)

    def _find_related_id(self, anime_id: int, relation_type: str) -> int | None:
        info = self._get_anime_info(anime_id)
        relations = ((info.get("relations") or {}).get("edges")) or []

        for edge in relations:
            if edge.get("relationType") != relation_type:
                continue

            node = edge.get("node") or {}
            node_id = node.get("id")
            if isinstance(node_id, int):
                return node_id

        return None

    def _find_first_main_entry(self, anime_id: int) -> int:
        current_id = anime_id
        visited = set()

        while current_id not in visited:
            visited.add(current_id)
            info = self._get_anime_info(current_id)
            relations = ((info.get("relations") or {}).get("edges")) or []

            prequel_id = None
            for edge in relations:
                if edge.get("relationType") != "PREQUEL":
                    continue

                node = edge.get("node") or {}
                node_id = node.get("id")
                node_title = self._preferred_title_from_node(node)
                node_format = node.get("format")

                if not isinstance(node_id, int):
                    continue

                if self._looks_like_non_season_entry(node_title, node_format):
                    continue

                prequel_id = node_id
                break

            if not prequel_id:
                return current_id

            current_id = prequel_id

        return anime_id

    def _get_direct_main_sequel(self, anime_id: int) -> int | None:
        info = self._get_anime_info(anime_id)
        relations = ((info.get("relations") or {}).get("edges")) or []

        for edge in relations:
            if edge.get("relationType") != "SEQUEL":
                continue

            node = edge.get("node") or {}
            node_id = node.get("id")
            node_title = self._preferred_title_from_node(node)
            node_format = node.get("format")

            if not isinstance(node_id, int):
                continue

            if self._looks_like_non_season_entry(node_title, node_format):
                continue

            return node_id

        return None

    def _find_season_by_chain(self, anime_id: int) -> int:
        first_id = self._find_first_main_entry(anime_id)
        current_id = first_id
        visited = set()
        season_number = 1

        while current_id not in visited:
            visited.add(current_id)

            if current_id == anime_id:
                return season_number

            sequel_id = self._get_direct_main_sequel(current_id)
            if not sequel_id:
                break

            current_id = sequel_id
            season_number += 1

        return 1

    def get_season(self, url: str) -> str:
        anime_id = self._extract_anime_id(url)

        explicit = self._extract_explicit_season(anime_id)
        if explicit is not None:
            season = explicit
        else:
            season = self._find_season_by_chain(anime_id)

        return f"S0{season}" if season <= 9 else f"S{season}"


class JikanAPI:
    def __init__(self):
        self._base_url = "https://api.jikan.moe/v4"
        self._headers = {
            "Accept": "application/json",
            "User-Agent": "AnimeSeasonResolver/1.0",
        }
        self._info_cache: dict[int, dict] = {}
        self._relations_cache: dict[int, list] = {}
        self._limiter = RateLimiter(max_calls=1, period=1.2)  # ~50 richieste/minuto, sotto i 60/min pubblici

    def _extract_mal_id(self, url: str) -> int:
        if url.isdigit():
            return int(url)

        match = re.search(r"myanimelist\.net/anime/(\d+)", url)
        if match:
            return int(match.group(1))

        raise ValueError(f"ID MyAnimeList non trovato in: {url}")

    def _get(self, endpoint: str) -> dict:
        self._limiter.wait()
        response = requests.get(
            f"{self._base_url}{endpoint}",
            headers=self._headers,
            timeout=15,
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise Exception("Risposta Jikan non valida")

        return data

    def _get_anime_info(self, anime_id: int) -> dict:
        if anime_id in self._info_cache:
            return self._info_cache[anime_id]

        data = self._get(f"/anime/{anime_id}/full")
        media = data.get("data")

        if not isinstance(media, dict):
            raise Exception(f"Anime MAL con ID {anime_id} non trovato")

        self._info_cache[anime_id] = media
        return media

    def _get_relations(self, anime_id: int) -> list:
        if anime_id in self._relations_cache:
            return self._relations_cache[anime_id]

        data = self._get(f"/anime/{anime_id}/relations")
        relations = data.get("data")

        if not isinstance(relations, list):
            relations = []

        self._relations_cache[anime_id] = relations
        return relations

    def _normalize_title(self, title: str) -> str:
        if not title:
            return ""

        title = title.strip()
        title = re.sub(r"\s+", " ", title)
        return title.strip()

    def _roman_to_int(self, token: str) -> int | None:
        roman_map = {
            "ii": 2, "iii": 3, "iv": 4, "v": 5,
            "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10,
        }
        return roman_map.get(token.lower())

    def _extract_season_number_from_text(self, title: str) -> int | None:
        if not title:
            return None

        clean_title = self._normalize_title(title)

        numeric_patterns = [
            r"\bseason\s*(\d+)\b",
            r"\b(\d+)(?:st|nd|rd|th)\s*season\b",
            r"\bs(?:eason)?\s*(\d{1,2})\b",
        ]

        for pattern in numeric_patterns:
            match = re.search(pattern, clean_title, re.IGNORECASE)
            if match:
                return int(match.group(1))

        ordinal_words = {
            "second season": 2,
            "third season": 3,
            "fourth season": 4,
            "fifth season": 5,
            "sixth season": 6,
        }

        lowered = clean_title.lower()
        for key, value in ordinal_words.items():
            if key in lowered:
                return value

        roman_match = re.search(r"\b(ii|iii|iv|v|vi|vii|viii|ix|x)\b", clean_title, re.IGNORECASE)
        if roman_match:
            return self._roman_to_int(roman_match.group(1))

        return None

    def _extract_explicit_season(self, anime_id: int) -> int | None:
        info = self._get_anime_info(anime_id)
        titles = [
            info.get("title") or "",
            info.get("title_english") or "",
            info.get("title_japanese") or "",
        ]

        for title in titles:
            season = self._extract_season_number_from_text(title)
            if season is not None:
                return season

        return None

    def _looks_like_non_season_entry(self, title: str, kind: str | None) -> bool:
        normalized = self._normalize_title(title).lower()
        kind = (kind or "").lower()

        if kind in {"movie", "special", "ova", "ona", "music"}:
            return True

        patterns = [
            r"\bmovie\b", r"\bspecial\b", r"\bova\b", r"\bona\b",
            r"\brecap\b", r"\bsummary\b", r"\bedition\b", r"\bpilot\b",
            r"\bshorts?\b", r"\bcm\b", r"\bpv\b", r"\bpromo\b",
            r"\bpromotional\b", r"\bpreview\b",
        ]

        return any(re.search(pattern, normalized, re.IGNORECASE) for pattern in patterns)

    def _find_related_id(self, anime_id: int, relation_name: str) -> int | None:
        relations = self._get_relations(anime_id)

        for relation in relations:
            if (relation.get("relation") or "").upper() != relation_name.upper():
                continue

            entries = relation.get("entry") or []
            for entry in entries:
                mal_id = entry.get("mal_id")
                if isinstance(mal_id, int):
                    return mal_id

        return None

    def _find_first_main_entry(self, anime_id: int) -> int:
        current_id = anime_id
        visited = set()

        while current_id not in visited:
            visited.add(current_id)
            relations = self._get_relations(current_id)

            prequel_id = None
            for relation in relations:
                if (relation.get("relation") or "").upper() != "PREQUEL":
                    continue

                entries = relation.get("entry") or []
                for entry in entries:
                    mal_id = entry.get("mal_id")
                    title = entry.get("name") or ""
                    kind = entry.get("type") or ""

                    if not isinstance(mal_id, int):
                        continue

                    if self._looks_like_non_season_entry(title, kind):
                        continue

                    prequel_id = mal_id
                    break

                if prequel_id:
                    break

            if not prequel_id:
                return current_id

            current_id = prequel_id

        return anime_id

    def _get_direct_main_sequel(self, anime_id: int) -> int | None:
        relations = self._get_relations(anime_id)

        for relation in relations:
            if (relation.get("relation") or "").upper() != "SEQUEL":
                continue

            entries = relation.get("entry") or []
            for entry in entries:
                mal_id = entry.get("mal_id")
                title = entry.get("name") or ""
                kind = entry.get("type") or ""

                if not isinstance(mal_id, int):
                    continue

                if self._looks_like_non_season_entry(title, kind):
                    continue

                return mal_id

        return None

    def _find_season_by_chain(self, anime_id: int) -> int:
        first_id = self._find_first_main_entry(anime_id)
        current_id = first_id
        visited = set()
        season_number = 1

        while current_id not in visited:
            visited.add(current_id)

            if current_id == anime_id:
                return season_number

            sequel_id = self._get_direct_main_sequel(current_id)
            if not sequel_id:
                break

            current_id = sequel_id
            season_number += 1

        return 1

    def get_season(self, url: str) -> str:
        anime_id = self._extract_mal_id(url)

        explicit = self._extract_explicit_season(anime_id)
        if explicit is not None:
            season = explicit
        else:
            season = self._find_season_by_chain(anime_id)

        return f"S0{season}" if season <= 9 else f"S{season}"


class AnimeSeasonResolver:
    def __init__(self):
        self._anilist = AniListAPI()
        self._jikan = JikanAPI()

    def get_season(self, anilist_url: str | None = None, mal_url: str | None = None) -> str:
        if anilist_url:
            try:
                return self._anilist.get_season(anilist_url)
            except Exception as e:
                print(e)

        if mal_url:
            try:
                return self._jikan.get_season(mal_url)
            except Exception as e:
                print(e)

        return "S01"