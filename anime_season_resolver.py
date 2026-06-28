import re
import requests


class AniListAPI:
    def __init__(self):
        self._url = "https://graphql.anilist.co"
        self._headers = {"Content-Type": "application/json"}

    def _extract_anime_id(self, url: str) -> int:
        if url.isdigit():
            return int(url)

        match = re.search(r"anilist\.co/anime/(\d+)", url)
        if match:
            return int(match.group(1))

        raise ValueError(f"ID AniList non trovato in: {url}")

    def _post(self, query: str, variables: dict) -> dict:
        response = requests.post(
            self._url,
            json={"query": query, "variables": variables},
            headers=self._headers,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise Exception("Risposta AniList non valida")

        if data.get("errors"):
            raise Exception(f"Errore AniList: {data['errors']}")

        return data

    def _get_anime_info(self, anime_id: int) -> dict:
        query = """
        query ($id: Int) {
            Media(id: $id, type: ANIME) {
                id
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

        return media

    def _normalize_title(self, title: str) -> str:
        if not title:
            return ""

        title = title.strip()

        title = re.sub(r"\bpart\s*\d+\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bcour\s*\d+\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bmovie\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bova\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bona\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bspecial\b", "", title, flags=re.IGNORECASE)

        title = re.sub(r"\s+", " ", title).strip()
        return title

    def _extract_season_number_from_text(self, title: str) -> int | None:
        if not title:
            return None

        clean_title = self._normalize_title(title)

        explicit_patterns = [
            r"\bseason\s*(\d+)\b",
            r"\b(\d+)(?:st|nd|rd|th)?\s*season\b",
            r"\b(\d+)(?:st|nd|rd|th)\b",
            r"\bs(\d{1,2})\b",
        ]

        for pattern in explicit_patterns:
            match = re.search(pattern, clean_title, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _extract_season_from_title(self, anime_id: int) -> int | None:
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
            if not title:
                continue

            season = self._extract_season_number_from_text(title)
            if season is not None:
                return season

        return None

    def _has_prequel(self, anime_id: int) -> bool:
        info = self._get_anime_info(anime_id)
        relations = ((info.get("relations") or {}).get("edges")) or []
        return any(edge.get("relationType") == "PREQUEL" for edge in relations)

    def _is_alternative_version(self, anime_id: int) -> bool:
        info = self._get_anime_info(anime_id)
        title_data = info.get("title") or {}
        titles = [
            title_data.get("romaji") or "",
            title_data.get("english") or "",
            title_data.get("native") or "",
        ]
        patterns = ["√", "[A]", ": A", " Alternative", "Reboot"]

        for title in titles:
            if any(pattern in title for pattern in patterns):
                return True

        return False

    def _is_new_series(self, anime_id: int) -> bool:
        info = self._get_anime_info(anime_id)
        title_data = info.get("title") or {}
        titles = [
            title_data.get("romaji") or "",
            title_data.get("english") or "",
        ]

        for title in titles:
            normalized = self._normalize_title(title)
            if ":" in normalized and "Season" not in normalized and not re.search(r"\b\d+\b", normalized):
                return True

        return False

    def _find_first_anime(self, anime_id: int) -> int:
        current_id = anime_id
        visited = set()

        while current_id not in visited:
            visited.add(current_id)
            info = self._get_anime_info(current_id)
            relations = ((info.get("relations") or {}).get("edges")) or []

            prequel_id = None
            for edge in relations:
                if edge.get("relationType") == "PREQUEL":
                    node = edge.get("node") or {}
                    prequel_id = node.get("id")
                    break

            if not prequel_id:
                return current_id

            current_id = prequel_id

        return anime_id

    def _get_all_sequels(self, first_id: int) -> list[tuple[int, str]]:
        sequels = []
        current_id = first_id
        visited = set()

        while current_id not in visited:
            visited.add(current_id)

            info = self._get_anime_info(current_id)
            relations = ((info.get("relations") or {}).get("edges")) or []

            sequel_id = None
            sequel_title = ""

            for edge in relations:
                if edge.get("relationType") == "SEQUEL":
                    node = edge.get("node") or {}
                    sequel_id = node.get("id")
                    node_title = node.get("title") or {}
                    sequel_title = (
                        node_title.get("romaji")
                        or node_title.get("english")
                        or node_title.get("native")
                        or ""
                    )
                    break

            if not sequel_id:
                break

            if not self._is_alternative_version(sequel_id):
                sequels.append((sequel_id, sequel_title))

            current_id = sequel_id

        return sequels

    def _find_season_by_position(self, first_id: int, target_id: int) -> int:
        if self._is_new_series(target_id):
            return 1

        if self._is_alternative_version(target_id) and self._has_prequel(target_id):
            return 2

        if first_id == target_id:
            return 1

        sequels = self._get_all_sequels(first_id)

        for index, (sequel_id, _) in enumerate(sequels, start=2):
            if sequel_id == target_id:
                return index

        return 1

    def get_season(self, url: str) -> str:
        anime_id = self._extract_anime_id(url)
        season = self._extract_season_from_title(anime_id)

        if season is None:
            first_id = self._find_first_anime(anime_id)
            season = self._find_season_by_position(first_id, anime_id)

        return f"S0{season}" if season <= 9 else f"S{season}"


class JikanAPI:
    def __init__(self):
        self._base_url = "https://api.jikan.moe/v4"
        self._headers = {"Accept": "application/json"}

    def _extract_mal_id(self, url: str) -> int:
        if url.isdigit():
            return int(url)

        match = re.search(r"myanimelist\.net/anime/(\d+)", url)
        if match:
            return int(match.group(1))

        raise ValueError(f"ID MyAnimeList non trovato in: {url}")

    def _get(self, endpoint: str) -> dict:
        response = requests.get(
            f"{self._base_url}{endpoint}",
            headers=self._headers,
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        if not isinstance(data, dict):
            raise Exception("Risposta Jikan non valida")

        return data

    def _get_anime_info(self, anime_id: int) -> dict:
        data = self._get(f"/anime/{anime_id}/full")
        media = data.get("data")

        if not isinstance(media, dict):
            raise Exception(f"Anime MAL con ID {anime_id} non trovato")

        return media

    def _get_relations(self, anime_id: int) -> list:
        data = self._get(f"/anime/{anime_id}/relations")
        relations = data.get("data")

        if not isinstance(relations, list):
            return []

        return relations

    def _normalize_title(self, title: str) -> str:
        if not title:
            return ""

        title = title.strip()

        title = re.sub(r"\bpart\s*\d+\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bcour\s*\d+\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bmovie\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bova\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bona\b", "", title, flags=re.IGNORECASE)
        title = re.sub(r"\bspecial\b", "", title, flags=re.IGNORECASE)

        title = re.sub(r"\s+", " ", title).strip()
        return title

    def _extract_season_number_from_text(self, title: str) -> int | None:
        if not title:
            return None

        clean_title = self._normalize_title(title)

        explicit_patterns = [
            r"\bseason\s*(\d+)\b",
            r"\b(\d+)(?:st|nd|rd|th)?\s*season\b",
            r"\b(\d+)(?:st|nd|rd|th)\b",
            r"\bs(\d{1,2})\b",
        ]

        for pattern in explicit_patterns:
            match = re.search(pattern, clean_title, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _extract_season_from_title(self, anime_id: int) -> int | None:
        info = self._get_anime_info(anime_id)
        titles = [
            info.get("title") or "",
            info.get("title_english") or "",
            info.get("title_japanese") or ""
        ]

        for title in titles:
            if not title:
                continue

            season = self._extract_season_number_from_text(title)
            if season is not None:
                return season

        return None

    def _has_prequel(self, anime_id: int) -> bool:
        relations = self._get_relations(anime_id)
        for relation in relations:
            if (relation.get("relation") or "").upper() == "PREQUEL":
                return True
        return False

    def _is_alternative_version(self, anime_id: int) -> bool:
        info = self._get_anime_info(anime_id)
        titles = [
            info.get("title") or "",
            info.get("title_english") or "",
            info.get("title_japanese") or ""
        ]
        patterns = ["√", "[A]", ": A", " Alternative", "Reboot"]

        for title in titles:
            if any(pattern in title for pattern in patterns):
                return True

        return False

    def _is_new_series(self, anime_id: int) -> bool:
        info = self._get_anime_info(anime_id)
        titles = [
            info.get("title") or "",
            info.get("title_english") or ""
        ]

        for title in titles:
            normalized = self._normalize_title(title)
            if ":" in normalized and "Season" not in normalized and not re.search(r"\b\d+\b", normalized):
                return True

        return False

    def _find_first_anime(self, anime_id: int) -> int:
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
                if entries:
                    prequel_id = entries[0].get("mal_id")
                    break

            if not prequel_id:
                return current_id

            current_id = prequel_id

        return anime_id

    def _get_direct_sequel(self, anime_id: int) -> int | None:
        relations = self._get_relations(anime_id)

        for relation in relations:
            if (relation.get("relation") or "").upper() != "SEQUEL":
                continue

            entries = relation.get("entry") or []
            if entries:
                return entries[0].get("mal_id")

        return None

    def _get_all_sequels(self, first_id: int) -> list[int]:
        sequels = []
        current_id = first_id
        visited = set()

        while current_id not in visited:
            visited.add(current_id)
            sequel_id = self._get_direct_sequel(current_id)

            if not sequel_id:
                break

            if not self._is_alternative_version(sequel_id):
                sequels.append(sequel_id)

            current_id = sequel_id

        return sequels

    def _find_season_by_position(self, first_id: int, target_id: int) -> int:
        if self._is_new_series(target_id):
            return 1

        if self._is_alternative_version(target_id) and self._has_prequel(target_id):
            return 2

        if first_id == target_id:
            return 1

        sequels = self._get_all_sequels(first_id)

        for index, sequel_id in enumerate(sequels, start=2):
            if sequel_id == target_id:
                return index

        return 1

    def get_season(self, url: str) -> str:
        anime_id = self._extract_mal_id(url)
        season = self._extract_season_from_title(anime_id)

        if season is None:
            first_id = self._find_first_anime(anime_id)
            season = self._find_season_by_position(first_id, anime_id)

        return f"S0{season}" if season <= 9 else f"S{season}"


class AnimeSeasonResolver:
    def __init__(self):
        self._anilist = AniListAPI()
        self._jikan = JikanAPI()

    def get_season(self, anilist_url: str, mal_url: str) -> str:
        try:
            return self._anilist.get_season(anilist_url)
        except Exception:
            pass

        try:
            return self._jikan.get_season(mal_url)
        except Exception:
            pass

        return "S01"