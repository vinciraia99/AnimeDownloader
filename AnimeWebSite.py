from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict
import re
import threading
import signal
import multiprocessing as mp
from multiprocessing import Process, Queue
import queue as queue_mod
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from tqdm import tqdm


CHUNK_SIZE = 512 * 1024
NUM_SEGMENTS = 8

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 60

MAX_RETRIES_PER_EPISODE = 20
INITIAL_RETRY_DELAY = 2.0
MAX_RETRY_DELAY = 60.0

USER_AGENT = "Mozilla/5.0"


def _build_session() -> requests.Session:
    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=0,
        status=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["HEAD", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _is_retryable_exception(exc: Exception) -> bool:
    if isinstance(exc, requests.exceptions.Timeout):
        return True

    if isinstance(exc, requests.exceptions.ConnectionError):
        msg = str(exc).lower()
        if "read timed out" in msg or "timed out" in msg:
            return True
        return True

    if isinstance(exc, requests.exceptions.RequestException):
        return True

    return False


def _compute_retry_delay(attempt: int) -> float:
    delay = INITIAL_RETRY_DELAY * (2 ** (attempt - 1))
    return min(delay, MAX_RETRY_DELAY)


def _safe_unlink(path: Path) -> None:
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass


def _prepare_tmp_file(tmp_path: Path, total_bytes: int) -> None:
    with open(tmp_path, "wb") as f:
        if total_bytes > 0:
            f.seek(total_bytes - 1)
            f.write(b"\0")


def _download_segment(
    session: requests.Session,
    url: str,
    start: int,
    end: int,
    tmp_path: str,
    file_lock: threading.Lock,
    progress_lock: threading.Lock,
    shared_progress: Dict[str, int],
    advance_cb,
    stop_flag: threading.Event,
    timeout: int,
) -> None:
    headers = {"Range": f"bytes={start}-{end}"}
    local_written = start

    with session.get(
        url,
        headers=headers,
        stream=True,
        timeout=(CONNECT_TIMEOUT, timeout),
    ) as r:
        r.raise_for_status()

        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            if stop_flag.is_set():
                return

            if not chunk:
                continue

            with file_lock:
                with open(tmp_path, "r+b") as f:
                    f.seek(local_written)
                    f.write(chunk)

            local_written += len(chunk)

            with progress_lock:
                shared_progress["bytes"] += len(chunk)

            advance_cb(len(chunk))


def _download_single_stream(
    session: requests.Session,
    url: str,
    tmp: Path,
    queue_result,
    name: str,
    timeout: int,
) -> None:
    with session.get(
        url,
        stream=True,
        timeout=(CONNECT_TIMEOUT, timeout),
    ) as r:
        r.raise_for_status()

        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if not chunk:
                    continue
                f.write(chunk)
                queue_result.put(("advance", name, len(chunk)))


def _download_segmented(
    session: requests.Session,
    url: str,
    tmp: Path,
    total_bytes: int,
    queue_result,
    name: str,
    timeout: int,
) -> None:
    _prepare_tmp_file(tmp, total_bytes)

    file_lock = threading.Lock()
    progress_lock = threading.Lock()
    stop_flag = threading.Event()
    segment_errors: List[Exception] = []
    error_lock = threading.Lock()
    shared_progress = {"bytes": 0}

    def advance_cb(n: int):
        queue_result.put(("advance", name, n))

    def run_segment(seg_start: int, seg_end: int):
        try:
            _download_segment(
                session=session,
                url=url,
                start=seg_start,
                end=seg_end,
                tmp_path=str(tmp),
                file_lock=file_lock,
                progress_lock=progress_lock,
                shared_progress=shared_progress,
                advance_cb=advance_cb,
                stop_flag=stop_flag,
                timeout=timeout,
            )
        except Exception as e:
            stop_flag.set()
            with error_lock:
                segment_errors.append(e)

    seg_size = total_bytes // NUM_SEGMENTS
    threads: List[threading.Thread] = []

    for i in range(NUM_SEGMENTS):
        seg_start = i * seg_size
        seg_end = (seg_start + seg_size - 1) if i < NUM_SEGMENTS - 1 else (total_bytes - 1)

        t = threading.Thread(
            target=run_segment,
            args=(seg_start, seg_end),
            daemon=True,
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    if segment_errors:
        raise segment_errors[0]

    final_size = tmp.stat().st_size if tmp.exists() else 0
    if final_size != total_bytes:
        raise IOError(f"File temporaneo incompleto: attesi {total_bytes} byte, trovati {final_size}")


def _download_one_worker(
    ep: Dict,
    download_dir_str: str,
    queue_result,
    timeout: int = READ_TIMEOUT,
    max_retries: int = MAX_RETRIES_PER_EPISODE,
) -> None:
    name = ep["name"]
    url = ep["url"]
    download_dir = Path(download_dir_str)
    dest = download_dir / name
    tmp = download_dir / f"{name}.tmp"

    session = _build_session()

    try:
        for attempt in range(1, max_retries + 1):
            attempt_started = False

            try:
                _safe_unlink(tmp)

                head = session.head(
                    url,
                    timeout=(CONNECT_TIMEOUT, 15),
                    allow_redirects=True,
                )

                total_bytes = int(head.headers.get("content-length", 0) or 0)
                supports_range = (
                    head.headers.get("Accept-Ranges", "none").lower() == "bytes"
                    and total_bytes > 0
                )

                if attempt == 1:
                    queue_result.put(("start", name, total_bytes))

                queue_result.put(("retry", name, f"Tentativo {attempt}/{max_retries}"))

                attempt_started = True

                if supports_range:
                    _download_segmented(
                        session=session,
                        url=url,
                        tmp=tmp,
                        total_bytes=total_bytes,
                        queue_result=queue_result,
                        name=name,
                        timeout=timeout,
                    )
                else:
                    _download_single_stream(
                        session=session,
                        url=url,
                        tmp=tmp,
                        queue_result=queue_result,
                        name=name,
                        timeout=timeout,
                    )

                tmp.replace(dest)
                queue_result.put(("done", name, None))
                return

            except Exception as e:
                _safe_unlink(tmp)

                retryable = _is_retryable_exception(e)

                if attempt >= max_retries or not retryable:
                    raise

                delay = _compute_retry_delay(attempt)
                if attempt_started:
                    queue_result.put(
                        ("retry_wait", name, f"{type(e).__name__}: {e} --- nuovo tentativo tra {delay:.1f}s")
                    )
                time.sleep(delay)

        raise RuntimeError("Retry esauriti")

    except Exception as e:
        _safe_unlink(tmp)
        queue_result.put(("error", name, str(e)))

    finally:
        try:
            session.close()
        except Exception:
            pass


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
            _safe_unlink(tmp)

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
        tqdm.write(f"Retry per episodio: {MAX_RETRIES_PER_EPISODE}")
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

                        elif msg_type == 'retry_wait':
                            tqdm.write(f"[RETRY] {name}: {value}")

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