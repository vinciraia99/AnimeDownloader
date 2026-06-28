from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict
import re
import threading
import signal
import multiprocessing as mp
from multiprocessing import Process, Queue
import queue as queue_mod

import requests
from tqdm import tqdm


CHUNK_SIZE = 512 * 1024
NUM_SEGMENTS = 8


def _download_segment(
    url: str,
    start: int,
    end: int,
    tmp_path: str,
    lock: threading.Lock,
    advance_cb,
    timeout: int = 60,
) -> None:
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Range": f"bytes={start}-{end}",
    }
    with requests.get(url, headers=headers, stream=True, timeout=(10, timeout)) as r:
        r.raise_for_status()
        written = start
        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            if not chunk:
                continue
            with lock:
                with open(tmp_path, "r+b") as f:
                    f.seek(written)
                    f.write(chunk)
            written += len(chunk)
            advance_cb(len(chunk))


def _download_one_worker(ep: Dict, download_dir_str: str, queue_result, timeout: int = 60) -> None:
    name = ep["name"]
    url = ep["url"]
    download_dir = Path(download_dir_str)
    dest = download_dir / name
    tmp = download_dir / f"{name}.tmp"

    try:
        head = requests.head(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True,
        )
        total_bytes = int(head.headers.get("content-length", 0) or 0)
        supports_range = (
            head.headers.get("Accept-Ranges", "none").lower() == "bytes"
            and total_bytes > 0
        )

        queue_result.put(("start", name, total_bytes))

        if supports_range:
            with open(tmp, "wb") as f:
                f.seek(total_bytes - 1)
                f.write(b"\0")

            lock = threading.Lock()

            def advance_cb(n: int):
                queue_result.put(("advance", name, n))

            seg_size = total_bytes // NUM_SEGMENTS
            threads = []
            for i in range(NUM_SEGMENTS):
                seg_start = i * seg_size
                seg_end = (seg_start + seg_size - 1) if i < NUM_SEGMENTS - 1 else (total_bytes - 1)
                t = threading.Thread(
                    target=_download_segment,
                    args=(url, seg_start, seg_end, str(tmp), lock, advance_cb, timeout),
                    daemon=True,
                )
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

        else:
            with requests.get(
                url,
                stream=True,
                timeout=(10, timeout),
                headers={"User-Agent": "Mozilla/5.0"},
            ) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                        if not chunk:
                            continue
                        f.write(chunk)
                        queue_result.put(("advance", name, len(chunk)))

        tmp.replace(dest)
        queue_result.put(("done", name, None))

    except Exception as e:
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass
        queue_result.put(("error", name, str(e)))


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
            tmp = download_dir / f"{ep['name']}.tmp"
            if tmp.exists():
                try:
                    tmp.unlink()
                except Exception:
                    pass

    def downloadAnime(
        self,
        start: int = -1,
        listEpisodi: Optional[List[Dict]] = None,
        max_workers: int = 9,
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
                tqdm.write(f"[SKIP] {ep['name']} --- nessun URL")
            else:
                pending.append(ep)

        if not pending:
            self._remove_incomplete_file(incomplete_file)
            self.incomplete = False
            return True

        total_eps = len(pending)
        tqdm.write(f"\nScarico {total_eps} episodi in: {download_dir}")
        tqdm.write("Ctrl+C per fermare\n")

        stop_event = threading.Event()

        def _sigint_handler(sig, frame):
            stop_event.set()

        original_sigint = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, _sigint_handler)

        failed: List[str] = []
        download_dir_str = str(download_dir)
        result_queue: Queue = mp.Queue()
        processes: List[Process] = []
        started = 0
        completed = 0
        started_names = set()
        total_bytes_expected = 0

        try:
            with tqdm(total=total_eps, desc='Episodi completati', unit='ep', dynamic_ncols=True, position=0) as episodes_bar, \
                 tqdm(total=0, desc='Dati scaricati', unit='B', unit_scale=True, unit_divisor=1024, dynamic_ncols=True, position=1) as bytes_bar:

                while completed < total_eps:
                    alive_count = sum(1 for p in processes if p.is_alive())
                    while not stop_event.is_set() and started < total_eps and alive_count < max_workers:
                        ep = pending[started]
                        p = Process(target=_download_one_worker, args=(ep, download_dir_str, result_queue))
                        p.start()
                        processes.append(p)
                        started += 1
                        alive_count += 1

                    if stop_event.is_set():
                        break

                    try:
                        msg_type, name, value = result_queue.get(timeout=0.2)

                        if msg_type == 'start':
                            if name not in started_names:
                                started_names.add(name)
                                if value and value > 0:
                                    total_bytes_expected += int(value)
                                    bytes_bar.total = total_bytes_expected
                                    bytes_bar.refresh()

                        elif msg_type == 'advance':
                            bytes_bar.update(int(value))

                        elif msg_type == 'done':
                            completed += 1
                            episodes_bar.update(1)
                            tqdm.write(f"[OK]  {name}")

                        elif msg_type == 'error':
                            completed += 1
                            episodes_bar.update(1)
                            failed.append(name)
                            tqdm.write(f"[ERR] {name}: {value}")

                    except queue_mod.Empty:
                        pass

                    alive_processes = []
                    for p in processes:
                        if p.is_alive():
                            alive_processes.append(p)
                        else:
                            try:
                                p.join(timeout=0.05)
                            except Exception:
                                pass
                    processes = alive_processes

        finally:
            if stop_event.is_set():
                for p in processes:
                    if p.is_alive():
                        try:
                            p.terminate()
                            p.join(timeout=2)
                        except Exception:
                            pass
            else:
                for p in processes:
                    try:
                        p.join(timeout=2)
                    except Exception:
                        pass
            signal.signal(signal.SIGINT, original_sigint)

        if stop_event.is_set():
            tqdm.write("\n[!] Download interrotto.")
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