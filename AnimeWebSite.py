from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, List, Dict
import re
import threading
import signal

import requests
from tqdm import tqdm


class AnimeWebSite:
    def __init__(self, url: str):
        self.url = url
        self.incomplete = False
        self.airing = False
        self.name: Optional[str] = None
        self._indexanime = 1

    def _sanitize_name(self, value: str) -> str:
        value = (value or "Anime").strip()
        value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', value)
        value = re.sub(r'\s+', ' ', value).strip(' .')
        return value or 'Anime'

    def _anime_dir_name(self) -> str:
        return self._sanitize_name(self.name or 'Anime')

    def _create_or_check_download_dir(self) -> tuple[Path, set[str]]:
        download_dir = Path.cwd() / self._anime_dir_name()
        download_dir.mkdir(parents=True, exist_ok=True)
        downloaded = {
            f.name for f in download_dir.iterdir()
            if f.is_file() and f.suffix.lower() == '.mp4'
        }
        return download_dir, downloaded

    def _create_airing_file(self, directory: Path) -> None:
        airing_file = directory / '.url'
        if self.airing and not airing_file.exists():
            airing_file.write_text(self.url, encoding='utf-8')

    def _create_incomplete_file(self, directory: Path) -> Path:
        incomplete_file = directory / '.incomplete'
        if not incomplete_file.exists():
            incomplete_file.write_text(self.url, encoding='utf-8')
        return incomplete_file

    def _remove_incomplete_file(self, incomplete_file: Path) -> None:
        if incomplete_file.exists():
            incomplete_file.unlink()

    def _cleanup_tmp_files(self, download_dir: Path, pending: List[Dict]) -> None:
        for ep in pending:
            tmp1 = download_dir / f"{ep['name']}.tmp"
            tmp2 = (download_dir / ep['name']).with_suffix('.tmp')
            if tmp1.exists():
                tmp1.unlink(missing_ok=True)
            if tmp2.exists():
                tmp2.unlink(missing_ok=True)

    def downloadAnime(
        self,
        start: int = -1,
        listEpisodi: Optional[List[Dict]] = None,
        max_workers: int = 6,
    ):
        if listEpisodi is None:
            listEpisodi = self.getEpisodeList(start)

        if not listEpisodi:
            raise Exception('Lista episodi vuota o non recuperata')

        download_dir, already_downloaded = self._create_or_check_download_dir()
        incomplete_file = self._create_incomplete_file(download_dir)
        self._create_airing_file(download_dir)
        self.incomplete = True

        pending: List[Dict] = []
        for ep in listEpisodi:
            if ep['name'] in already_downloaded:
                tqdm.write(f"[SKIP] {ep['name']} già scaricato")
            elif not ep.get('url'):
                tqdm.write(f"[SKIP] {ep['name']} — nessun URL")
            else:
                pending.append(ep)

        if not pending:
            self._remove_incomplete_file(incomplete_file)
            self.incomplete = False
            return True

        total_eps = len(pending)
        tqdm.write(f"\nScarico {total_eps} episodi in: {download_dir}")
        tqdm.write(f"Worker paralleli: {max_workers}")
        tqdm.write('Ctrl+C per fermare\n')

        stop_event = threading.Event()
        interrupted = [False]
        failed: List[str] = []
        failed_lock = threading.Lock()

        def _sigint_handler(sig, frame):
            interrupted[0] = True
            stop_event.set()
            tqdm.write('\n[!] Interruzione richiesta, arresto dei download...')

        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, _sigint_handler)

        def _download_one(ep: Dict) -> bool:
            name = ep['name']
            url = ep['url']
            dest = download_dir / name
            tmp = download_dir / f"{name}.tmp"

            try:
                with requests.get(
                    url,
                    stream=True,
                    timeout=(10, 30),
                    headers={'User-Agent': 'Mozilla/5.0'},
                ) as r:
                    r.raise_for_status()
                    total = int(r.headers.get('content-length', 0))

                    with tqdm(
                        total=total if total > 0 else None,
                        desc=name[:45],
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        dynamic_ncols=True,
                        leave=True,
                    ) as bar:
                        with open(tmp, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=512 * 1024):
                                if stop_event.is_set():
                                    raise KeyboardInterrupt
                                if not chunk:
                                    continue
                                f.write(chunk)
                                bar.update(len(chunk))

                if stop_event.is_set():
                    raise KeyboardInterrupt

                tmp.replace(dest)
                tqdm.write(f"[OK]  {name}")
                return True

            except KeyboardInterrupt:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
                raise

            except Exception as e:
                if tmp.exists():
                    tmp.unlink(missing_ok=True)
                tqdm.write(f"[ERR] {name}: {e}")
                return False

        try:
            with tqdm(
                total=total_eps,
                desc='Episodi completati',
                unit='ep',
                colour='cyan',
                dynamic_ncols=True,
                position=0,
            ) as overall:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {executor.submit(_download_one, ep): ep for ep in pending}

                    for future in as_completed(futures):
                        if stop_event.is_set():
                            for f in futures:
                                f.cancel()
                            break

                        ep = futures[future]
                        try:
                            ok = future.result()
                            if not ok:
                                with failed_lock:
                                    failed.append(ep['name'])
                            overall.update(1)
                        except KeyboardInterrupt:
                            interrupted[0] = True
                            stop_event.set()
                            for f in futures:
                                f.cancel()
                            break
                        except Exception as e:
                            tqdm.write(f"[ERR] {ep['name']}: {e}")
                            with failed_lock:
                                failed.append(ep['name'])
                            overall.update(1)
        finally:
            signal.signal(signal.SIGINT, original_sigint)

        if interrupted[0]:
            self._cleanup_tmp_files(download_dir, pending)
            raise KeyboardInterrupt

        if failed:
            tqdm.write(f"\n[WARN] {len(failed)} episodi falliti:")
            for name in failed:
                tqdm.write(f"  - {name}")
            return failed

        self._remove_incomplete_file(incomplete_file)
        self.incomplete = False
        return True
