# AnimeDownloader

## Warning

This tool has not yet been fully translated into English, and the currently supported sources only provide Italian anime content.

## Info

This Python script allows automatic downloading of anime episodes from the following site:

- AnimeWorld - Thanks to the developer of [AnimeWorld-API](https://github.com/MainKronos/AnimeWorld-API)

## Usage

The `anime.py` file allows downloading an entire anime season by receiving the anime URL as input.

It can receive the URL in two ways:

### 1. Prompted at runtime

```text
Enter the anime URL to download: https://example.com
```

### 2. Passed as an argument

```bash
python anime.py "https://example.com"
```

### 3. Passed as an argument with worker count

```bash
python anime.py "https://example.com" --max-workers=9
```

Both of the following forms are supported:

```bash
python anime.py "https://example.com" --max-workers=9
python anime.py "https://example.com" --max-worker=9
```

If the URL is not provided from the command line, the script switches to interactive mode and asks for it in the terminal.

## updater.py

The `updater.py` file checks anime already tracked through `.url`, `.incomplete`, or `url` files stored in local folders.

The script:

- reads anime already stored on disk;
- extracts episode numbers from `.mp4` files;
- checks whether new episodes are available online;
- downloads only missing or newer episodes;
- automatically moves to the next directory if an error occurs.

### Basic usage

```bash
python updater.py
```

### Usage with worker count

```bash
python updater.py --max-workers=9
```

Both of the following forms are supported:

```bash
python updater.py --max-workers=9
python updater.py --max-worker=9
```

## Available arguments

| Script | Argument | Description |
|---|---|---|
| `anime.py` | `URL` | URL of the anime to download |
| `anime.py` | `--max-workers` / `--max-worker` | Maximum number of parallel downloads |
| `updater.py` | `--max-workers` / `--max-worker` | Maximum number of parallel downloads during updates |

## Installation

1. Install [Python 3](https://www.python.org/downloads/).
2. Download the [repo](https://github.com/vinciraia99/AnimeDownloader/archive/refs/heads/main.zip) or clone it with:

```bash
git clone https://github.com/vinciraia99/AnimeDownloader.git
```

3. Install the `requirements.txt` file included in the repo:

```bash
pip install -r requirements.txt
```

4. Run `python anime.py` to start using the script.
5. To update ongoing anime, run `python updater.py`.

## Quick examples

```bash
python anime.py "https://www.animeworld.ac/play/farming-life-in-another-world-2.SV5W0/h7ORaq0xHW"
python anime.py "https://www.animeworld.ac/play/farming-life-in-another-world-2.SV5W0/h7ORaq0xHW" --max-workers=9
python updater.py --max-workers=9
```
