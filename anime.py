import argparse
import multiprocessing
import traceback

from utility import getAnimeClass, cleanProgram, customPrint


def parse_args():
    parser = argparse.ArgumentParser(description="Anime downloader")
    parser.add_argument(
        "url",
        nargs="?",
        help="URL dell'anime da scaricare"
    )
    parser.add_argument(
        "--max-workers",
        "--max-worker",
        dest="max_workers",
        type=int,
        default=12,
        help="Numero massimo di download paralleli (default: 12)",
    )
    return parser.parse_args()


def download_from_url(my_url: str, max_workers: int):
    anime = getAnimeClass(my_url)
    if anime is None:
        print('Url non valido. Riprova')
        return None

    result = anime.downloadAnime(max_workers=max_workers)
    if result is None:
        print('Url non valido. Riprova')
        return None

    customPrint("Ho scaricato l'anime : " + anime.name)
    return anime


def main():
    anime = None
    try:
        args = parse_args()

        if args.url:
            print(args.url)
            anime = download_from_url(args.url, args.max_workers)
        else:
            while True:
                my_url = input("Inserisci l'url dell'anime da scaricare: ").strip()
                if not my_url:
                    print('Inserisci un URL valido.')
                    continue

                anime = download_from_url(my_url, args.max_workers)
                if anime is not None:
                    break

    except KeyboardInterrupt:
        try:
            cleanProgram(anime)
        except Exception:
            pass
    except Exception:
        customPrint('Eccezione trovata')
        customPrint(traceback.format_exc())
        try:
            cleanProgram(anime)
        except Exception:
            pass


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()