import os
import string

import progressbar
import requests
from progressbar import DataSize, FileTransferSpeed, Bar, Percentage
from AnimeWorld import AnimeWorld

pbar = None


def customPrint(text: string):
    print(text)
    sendTelegram(text)


def cleanProgram(anime):
    if anime is not None:
        if anime.incomplete is True:
            print()
            print("Pulisco i file temporanei...")
            for file in os.listdir(os.getcwd()):
                if os.path.isdir(file):
                    for subpath in os.listdir(os.path.join(os.getcwd(), file)):
                        if subpath.endswith(".tmp"):
                            os.remove(os.path.join(os.getcwd(), file, subpath))
                if file.endswith(".tmp"):
                    os.remove(file)
    print("Chiudo il programma")
    exit(0)


def setChromeOption():
    options = OptionChrome()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-logging')
    options.add_argument('--no-sandbox')
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return options

def getAnimeClass(url: string):
    if "animeworld" in url:
        return AnimeWorld(url)


def progressBar(block_num, block_size, total_size):
    global pbar
    if pbar is None:
        widgets = ['Download in corso:', Percentage(), ' ',
                   Bar(marker='#'), ' ',
                   FileTransferSpeed(), ' ', DataSize(), "/",
                   DataSize(variable="max_value"), ' ', progressbar.ETA(format='ETA:%(eta)8s')]
        pbar = progressbar.ProgressBar(maxval=total_size, widgets=widgets)
        pbar.start()

    downloaded = block_num * block_size
    if downloaded < total_size:
        pbar.update(downloaded)
    else:
        pbar.finish()
        pbar = None


percentuale = 0


def sendTelegram(msg: string):
    if os.path.exists(os.path.join(os.getcwd(), "telegram.setting")):
        file = open(os.path.join(os.getcwd(), "telegram.setting"), 'r')
        line = file.readline()
        TOKEN = line.replace('\n', '')
        line = file.readline()
        CHAT = line.replace('\n', '')
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT}&text={msg}"
        requests.get(url)
