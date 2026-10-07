"""Extrait vidéo d'un appel noté, pour une publication : l'interface de démo filmée image par image, avec le son.

Aucune requête. Outils locaux uniquement : Chrome sans interface, piloté par son protocole de débogage,
et ffmpeg (paquet imageio-ffmpeg). L'interface est ouverte en mode « extrait » (seules les alertes de la fenêtre
s'affichent) et en mode « rendu » (le temps est avancé par window.figer(t), image par image).
Dépendances, en plus de requirements.txt : pip install imageio-ffmpeg websocket-client

Sortie : audio/extraits/appel-XX-extrait.mp3 (le son seul) et appel-XX-extrait.mp4 (1920 x 1080, 25 images/s)
Usage : python scripts/extrait_video.py 03 53.3 96.5 [--theme light|dark]
"""
import argparse
import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import websocket

sys.path.insert(0, str(Path(__file__).parent))
from effet_telephone import ecrire_wav, lire_wav  # noqa: E402
from encoder_mp3 import encoder  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
PORT = 9333
IMAGES_S = 25
LARGEUR, HAUTEUR, ECHELLE = 1440, 810, 4 / 3  # rendu en 1920 x 1080
FONDU_S = 0.3


def couper_audio(appel, debut, fin, wav):
    """Le son de l'extrait, avec un fondu court au début et à la fin pour éviter les clics."""
    signal, taux = lire_wav(ROOT / "audio" / "appels" / f"appel-{appel}.wav")
    morceau = signal[int(debut * taux):int(fin * taux)].astype(float)
    n = int(FONDU_S * taux)
    morceau[:n] *= np.linspace(0, 1, n)
    morceau[-n:] *= np.linspace(1, 0, n)
    ecrire_wav(wav, morceau, taux)


class Page:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, suppress_origin=True)
        self.n = 0

    def envoyer(self, methode, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": methode, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self.n:
                if "error" in message:
                    sys.exit(f"{methode} : {message['error']}")
                return message.get("result", {})

    def evaluer(self, expression):
        return self.envoyer("Runtime.evaluate", expression=expression, returnByValue=True).get("result", {}).get("value")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("appel")
    p.add_argument("debut", type=float)
    p.add_argument("fin", type=float)
    p.add_argument("--theme", default="light", choices=["light", "dark"])
    args = p.parse_args()
    appel = f"{int(args.appel):02d}"
    sortie = ROOT / "audio" / "extraits"
    sortie.mkdir(parents=True, exist_ok=True)
    mp3, mp4 = sortie / f"appel-{appel}-extrait.mp3", sortie / f"appel-{appel}-extrait.mp4"

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "extrait.wav"
        couper_audio(appel, args.debut, args.fin, wav)
        encoder(wav, mp3)

        chrome = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PORT}", f"--user-data-dir={tmp}/profil",
                                   "--hide-scrollbars", "--disable-gpu", "--mute-audio", f"--window-size={LARGEUR},{HAUTEUR}", "about:blank"],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    cibles = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/list").read())
                    break
                except OSError:
                    time.sleep(0.2)
            page = Page(next(c for c in cibles if c["type"] == "page")["webSocketDebuggerUrl"])
            page.envoyer("Emulation.setDeviceMetricsOverride", width=LARGEUR, height=HAUTEUR, deviceScaleFactor=ECHELLE, mobile=False)
            url = ((ROOT / "ui" / "index.html").as_uri() +
                   f"?appel={appel}&vue=ecoute&debut={args.debut}&fin={args.fin}&t={args.debut}&rendu=1&theme={args.theme}")
            page.envoyer("Page.navigate", url=url)
            for _ in range(100):  # page, données et polices chargées
                if page.evaluer("document.readyState === 'complete' && document.fonts.status === 'loaded' && typeof window.figer === 'function'"):
                    break
                time.sleep(0.1)
            for _ in range(40):  # la transcription rejoint sa position de départ avant la première image
                page.evaluer(f"figer({args.debut})")

            images = int((args.fin - args.debut) * IMAGES_S)
            ffmpeg = subprocess.Popen([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                                       "-f", "image2pipe", "-framerate", str(IMAGES_S), "-c:v", "mjpeg", "-i", "-",
                                       "-i", str(wav), "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                                       "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-shortest", "-movflags", "+faststart", str(mp4)],
                                      stdin=subprocess.PIPE)
            for i in range(images):
                page.evaluer(f"figer({args.debut + i / IMAGES_S})")
                image = page.envoyer("Page.captureScreenshot", format="jpeg", quality=93)["data"]
                ffmpeg.stdin.write(base64.b64decode(image))
                if i % (IMAGES_S * 5) == 0:
                    print(f"{i / IMAGES_S:.0f} s / {images / IMAGES_S:.0f} s", flush=True)
            ffmpeg.stdin.close()
            ffmpeg.wait()
        finally:
            chrome.terminate()
            chrome.wait()
    print(f"{mp3.relative_to(ROOT)} et {mp4.relative_to(ROOT)} : {args.fin - args.debut:.1f} s, {mp4.stat().st_size / 1e6:.1f} Mo")


if __name__ == "__main__":
    main()
