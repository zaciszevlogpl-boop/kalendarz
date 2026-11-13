"""Najnowsze odcinki Zacisza na stronę (sekcja „Ostatnio na Zaciszu”, 13.11.2026).

Czyta publiczny kanał RSS YouTube, pomija Shorty, bierze 6 najnowszych i zapisuje odcinki.json.
Robot (workflows/klucze.yml) odpala to co godzinę, build.py przy każdym budowaniu strony.
Gdy YouTube nie odpowie albo nic nie znajdzie, stary plik zostaje bez zmian.

Użycie:
  python3 odcinki.py                      zapisuje ./odcinki.json
  python3 odcinki.py --wyjscie site/x.json
  python3 odcinki.py --sprawdz            jak wyżej + porównuje z opublikowanym (GITHUB_OUTPUT odcinki=true/false)
"""
import html, json, os, re, sys, urllib.error, urllib.request

KANAL = "UCL5rGxNoo_8dgVaPEYo88dw"
RSS = f"https://www.youtube.com/feeds/videos.xml?channel_id={KANAL}"
LIVE = "https://www.zaciszevlog.pl/odcinki.json"
ILE = 6
UA = {"User-Agent": "Mozilla/5.0 (zaciszevlog.pl)"}
EMOJI = re.compile("[☀-➿⭐\U0001f300-\U0001faff]️?")


def pobierz(url, timeout=20):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


class BezPrzekierowan(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def kod(url):
    """Kod odpowiedzi bez podążania za przekierowaniem."""
    try:
        with urllib.request.build_opener(BezPrzekierowan).open(urllib.request.Request(url, headers=UA), timeout=15) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def tytul(surowy):
    """„NIE LEŻAŁAM PRZED TELEWIZOREM 🍂 spływ Dunajcem… | vlog” → (Nie leżałam przed telewizorem, spływ Dunajcem…, Vlog)"""
    t = html.unescape(surowy).strip()
    typ = "Vlog" if re.search(r"\bvlog\b", t, re.I) else ("Pogadanka" if "☕" in t else "")
    t = re.sub(r"\s*\|\s*(spokojny\s+)?vlog\s*$", "", t, flags=re.I)
    m = EMOJI.search(t)
    glowny, pod = (t[:m.start()], t[m.end():]) if m else (t, "")
    glowny, pod = EMOJI.sub("", glowny).strip(" |"), EMOJI.sub("", pod).strip(" |")
    if glowny == glowny.upper() and re.search(r"[A-ZĄĆĘŁŃÓŚŹŻ]", glowny):
        glowny = glowny.lower()
        glowny = glowny[:1].upper() + glowny[1:]
    return glowny, pod, typ


def lista():
    x = pobierz(RSS).decode("utf-8")
    wynik = []
    for e in re.findall(r"<entry>(.*?)</entry>", x, re.S):
        vid = re.search(r"<yt:videoId>(.*?)<", e).group(1)
        surowy = re.search(r"<title>(.*?)</title>", e, re.S).group(1)
        dzien = re.search(r"<published>(\d{4})-(\d\d)-(\d\d)", e)
        if re.search(r"#shorts", surowy, re.I) or re.search(r"claude|anthropic|artifact", surowy, re.I):
            continue
        if kod(f"https://www.youtube.com/shorts/{vid}") == 200:  # Short bez #Shorts w tytule
            continue
        glowny, pod, typ = tytul(surowy)
        img = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
        if kod(img) != 200:
            img = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        wynik.append({"id": vid, "tytul": glowny, "pod": pod, "typ": typ,
                      "data": f"{dzien.group(3)}.{dzien.group(2)}", "img": img})
        if len(wynik) == ILE:
            break
    return wynik


def main():
    wyjscie = sys.argv[sys.argv.index("--wyjscie") + 1] if "--wyjscie" in sys.argv else "odcinki.json"
    try:
        nowe = lista()
    except Exception as e:
        nowe = []
        print("nie mogę odczytać kanału YouTube:", e)
    zmiana = False
    if len(nowe) >= 3:
        with open(wyjscie, "w", encoding="utf-8") as f:
            json.dump(nowe, f, ensure_ascii=False, indent=1)
        if "--sprawdz" in sys.argv:
            try:
                zmiana = json.loads(pobierz(f"{LIVE}?t={os.getpid()}")) != nowe
            except Exception as e:
                print("nie mogę odczytać opublikowanego odcinki.json:", e)
                zmiana = True
    else:
        print("za mało odcinków z kanału, zostaje stary plik")
    print(f"odcinki: {[o['id'] for o in nowe]}, trzeba publikować: {zmiana}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"odcinki={'true' if zmiana else 'false'}\n")


if __name__ == "__main__":
    main()
