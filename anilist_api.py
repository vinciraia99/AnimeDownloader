import re
import requests


class AniListAPI:
    def __init__(self):
        self._url = 'https://graphql.anilist.co'

    def _extract_anime_id(self, url: str) -> int:
        if url.isdigit():
            return int(url)
        pattern = r'anilist\.co/anime/(\d+)'
        match = re.search(pattern, url)
        if match:
            return int(match.group(1))
        raise ValueError(f"ID dell'anime non trovato in: {url}")

    def _get_anime_info(self, anime_id: int) -> dict:
        query = """query ($id: Int) {\n            Media(id: $id, type: ANIME) {\n                id\n                title { romaji english }\n                relations {\n                    edges {\n                        relationType\n                        node {\n                            id\n                            title { romaji }\n                        }\n                    }\n                }\n            }\n        }"""
        response = requests.post(
            self._url,
            json={'query': query, 'variables': {'id': anime_id}},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        data = response.json()
        media = data.get("data", {}).get("Media")
        if not media:
            raise Exception(f"Anime con ID {anime_id} non trovato")
        return media

    def _extract_season_from_title(self, anime_id: int) -> int:
        info = self._get_anime_info(anime_id)
        title = info.get("title", {}).get("romaji", "")
        english_title = info.get("title", {}).get("english", "")

        if not title:
            title = ""
        if not english_title:
            english_title = ""

        for t in [title, english_title]:
            if not t:
                continue
            match = re.search(r'(\d+)', t)
            if match:
                return int(match.group(1))

            match = re.search(r'Season\s*(\d+)', t, re.IGNORECASE)
            if match:
                return int(match.group(1))

            match = re.search(r'(\d+)\s*season', t, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def _get_all_sequels(self, first_id: int) -> list:
        sequels = []
        current_id = first_id

        while True:
            info = self._get_anime_info(current_id)
            relations = info.get("relations", {}).get("edges", [])

            found_next = False
            for edge in relations:
                if edge.get("relationType") == "SEQUEL":
                    sequel_id = edge.get("node", {}).get("id")
                    sequel_title = edge.get("node", {}).get("title", {}).get("romaji", "")
                    sequels.append((sequel_id, sequel_title))
                    current_id = sequel_id
                    found_next = True
                    break

            if not found_next:
                break

        return sequels

    def _find_first_anime(self, anime_id: int) -> int:
        current_id = anime_id
        while True:
            info = self._get_anime_info(current_id)
            relations = info.get("relations", {}).get("edges", [])
            prequel_found = None
            for edge in relations:
                if edge.get("relationType") == "PREQUEL":
                    prequel_found = edge.get("node", {}).get("id")
                    break
            if prequel_found:
                current_id = prequel_found
            else:
                return current_id

    def _find_season_by_position(self, first_id: int, target_id: int) -> int:
        sequels = self._get_all_sequels(first_id)

        if not sequels:
            return 1

        for i, (sequel_id, _) in enumerate(sequels):
            if sequel_id == target_id:
                return i + 2

        return 1

    def get_season(self, url: str) -> str:
        anime_id = self._extract_anime_id(url)

        season = self._extract_season_from_title(anime_id)

        if season is None:
            first_id = self._find_first_anime(anime_id)
            season = self._find_season_by_position(first_id, anime_id)

        return f"S0{season}" if season <= 9 else f"S{season}"