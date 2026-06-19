from __future__ import annotations

import argparse
import multiprocessing
import re
import traceback
import warnings
from pathlib import Path
from typing import Optional

from utility import *

warnings.filterwarnings("ignore")

MARKER_FILES = (".url", ".incomplete", "url")
EPISODE_REGEX = re.compile(r"(?:_Ep_(\d+))|(?:_S\d+EP(\d+))", re.IGNORECASE)


def parse_args():
    parser = argparse.ArgumentParser(description="Aggiorna gli anime già tracciati")
    parser.add_argument(
        "--max-workers",
        "--max-worker",
        dest="max_workers",
        type=int,
        default=12,
        help="Numero massimo di download paralleli (default: 12)",
    )
    return parser.parse_args()


def get_mp4_files(dirname: str) -> list[str]:
    folder = Path(os.getcwd()) / dirname
    try:
        if not folder.is_dir():
            return []
    except OSError:
        return []

    files = []
    try:
        for file in folder.iterdir():
            try:
                if file.is_file() and file.suffix.lower() == ".mp4":
                    files.append(file.name)
            except OSError:
                continue
    except OSError:
        return []

    return sorted(files)


def extract_episode_number(filename: str) -> Optional[int]:
    match = EPISODE_REGEX.search(filename)
    if not match:
        return None

    episode = match.group(1) or match.group(2)
    return int(episode)


def get_downloaded_episode_numbers(dirname: str) -> list[int]:
    numbers = []
    for filename in get_mp4_files(dirname):
        number = extract_episode_number(filename)
        if number is not None:
            numbers.append(number)
    return sorted(set(numbers))


def get_last_downloaded_episode(dirname: str) -> int:
    numbers = get_downloaded_episode_numbers(dirname)
    return max(numbers) if numbers else 0


def is_sequence_complete(dirname: str) -> bool:
    numbers = get_downloaded_episode_numbers(dirname)
    if not numbers:
        return False

    for i in range(1, len(numbers)):
        if numbers[i] != numbers[i - 1] + 1:
            return False
    return True


def delete_airing(dirname: str) -> bool:
    folder = Path(os.getcwd()) / dirname
    try:
        if not folder.is_dir():
            return False
    except OSError:
        return False

    for marker in (".url", "url"):
        marker_path = folder / marker
        try:
            if marker_path.is_file():
                marker_path.unlink()
                return True
        except OSError:
            continue
    return False


def read_tracking_url(dirname: str) -> Optional[str]:
    folder = Path(os.getcwd()) / dirname
    for marker in MARKER_FILES:
        marker_path = folder / marker
        try:
            if marker_path.is_file():
                return marker_path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
    return None


def find_tracked_dirs() -> list[str]:
    cwd = Path(os.getcwd())
    result = []

    try:
        entries = list(cwd.iterdir())
    except OSError:
        print("[ERR] Impossibile leggere la directory corrente")
        print(traceback.format_exc())
        return result

    for path in entries:
        try:
            if not path.is_dir():
                continue
        except OSError:
            print(f"[WARN] Directory non accessibile, salto: {path}")
            continue

        found = False
        for marker in MARKER_FILES:
            try:
                if (path / marker).is_file():
                    found = True
                    break
            except OSError:
                continue

        if found:
            result.append(path.name)

    return sorted(result)


def build_tracked_list() -> list[dict]:
    tracked = []

    for dirname in find_tracked_dirs():
        try:
            url = read_tracking_url(dirname)
            if not url:
                print(f"[WARN] URL non trovata per: {dirname}")
                continue

            tracked.append({
                "name": dirname,
                "url": url,
                "downloaded_numbers": get_downloaded_episode_numbers(dirname),
                "last_episode": get_last_downloaded_episode(dirname),
                "is_complete": is_sequence_complete(dirname),
            })
        except Exception:
            print(f"[ERR] Impossibile costruire i dati per: {dirname}")
            print(traceback.format_exc())
            continue

    return tracked


def filter_missing_episodes(episode_list: list[dict], downloaded_numbers: list[int]) -> list[dict]:
    already_downloaded = set(downloaded_numbers)
    filtered = []

    for ep in episode_list:
        try:
            ep_number = int(ep.get("number", 0))
        except Exception:
            ep_number = 0

        if ep_number not in already_downloaded:
            filtered.append(ep)

    return filtered


def process_anime(tracked: dict, index: int, total: int, max_workers: int):
    print(
        "== Verifico se ci sono nuovi episodi per l'anime "
        + str(index)
        + " di "
        + str(total)
        + " : "
        + tracked["name"]
        + " =="
    )

    my_url = tracked["url"]
    anime = getAnimeClass(my_url)
    if anime is None:
        print("Url non valido. Riprova")
        return None

    if tracked["is_complete"] and tracked["last_episode"] > 0:
        episode_list = anime.getEpisodeList(tracked["last_episode"])
    else:
        episode_list = anime.getEpisodeList()
        if episode_list is None:
            episode_list = []
        episode_list = filter_missing_episodes(episode_list, tracked["downloaded_numbers"])

    if episode_list is None:
        episode_list = []

    if len(episode_list) > 0:
        anime.downloadAnime(0, episode_list, max_workers=max_workers)
        if anime.airing is False and delete_airing(tracked["name"]):
            customPrint("L'anime " + anime.name + " non è più in corso")
        return anime.name

    print("Non ci sono nuovi episodi")

    if anime.airing is False and delete_airing(tracked["name"]):
        customPrint("L'anime " + anime.name + " non è più in corso")

    return None


def main():
    args = parse_args()
    updated = []
    anime = None

    try:
        tracked_list = build_tracked_list()

        for animeindex, tracked in enumerate(tracked_list, start=1):
            try:
                anime_name = process_anime(tracked, animeindex, len(tracked_list), args.max_workers)
                if anime_name:
                    updated.append(anime_name)
            except KeyboardInterrupt:
                raise
            except Exception:
                print(f"[ERR] Errore durante l'elaborazione della directory: {tracked['name']}")
                print(traceback.format_exc())
                continue

        if len(updated) > 0:
            text = "\nHo aggiornato i seguenti anime:"
            for name in updated:
                text += "\n" + name
            customPrint(text)
        else:
            customPrint("\nNessun nuovo episodio anime tra quelli in lista")

    except KeyboardInterrupt:
        try:
            cleanProgram(anime)
        except Exception:
            pass
    except Exception:
        customPrint("Eccezione trovata")
        customPrint(traceback.format_exc())
        try:
            cleanProgram(anime)
        except Exception:
            pass


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()