"""Najnowsze filmy z innych kanałów Gabrysi na stronę (zakładka „Inne kanały”, 17.11.2026).

Gabrysia 17.11: „na stronie zacisze vlog powinna być karta inne kanały Gabrysi, a tam filmy Janusza, afirmacji etc.”
Czyta publiczne kanały RSS YouTube z listy „tylko długie filmy” (UULF…, bez shortów i transmisji na żywo),
bierze po kilka najnowszych z każdego kanału i zapisuje kanaly.json = {klucz: [filmy]}.
Robot (workflows/klucze.yml) odpala to co godzinę, build.py przy każdym budowaniu strony.
Gdy YouTube nie odpowie dla któregoś kanału, ten kanał zostaje taki, jak był w starym pliku.

Użycie:
  python3 kanaly.py                      zapisuje ./kanaly.json
  python3 kanaly.py --wyjscie site/x.json
  python3 kanaly.py --sprawdz            jak wyżej + porównuje z opublikowanym (GITHUB_OUTPUT kanaly=true/false)
"""
import html, json, os, re, sys, urllib.error, urllib.request

# klucz = data-kanal w stronie; opcjonalnie od = pomijaj filmy starsze (RRRR-MM-DD), jezyk = es/de (tytuł bez zmian)
# Gabrysia 17.11: „tylko afirmacje i Janusza, najpierw ma być widoczny Janusz”
KANALY = [
    {"klucz": "janusz", "id": "UCwTQRRDyyPe9Mt5hwH0U8Pw", "ile": 3},
    {"klucz": "afirmacje", "id": "UCBFnoYXFZQW7WuvoUJEVTdg", "ile": 3},
]
LIVE = "https://www.zaciszevlog.pl/kanaly.json"
UA = {"User-Agent": "Mozilla/5.0 (zaciszevlog.pl)"}
EMOJI = re.compile("[☀-➿⭐⭐\U0001f300-\U0001faff]️?")
# skróty i nazwy, które w tytule zostają wielkimi literami / z wielkiej
SKROTY = {"IKE", "IKZE", "PPK", "ZUS", "VAT", "RRSO", "WIBOR", "WIRON", "BIK", "PIT", "NBP", "ETF", "KNF", "OFE", "BFG",
          "BLIK", "PKO", "ING", "USA", "UE", "AI", "GUS", "RPP", "PKB", "OC", "AC", "NFZ", "KRUS", "SMS", "PIN", "IBAN", "TV"}
NAZWY = {"JANUSZ": "Janusz", "JANUSZA": "Janusza", "JANUSZOWI": "Januszowi", "JANUSZU": "Januszu",
         "POLSKA": "Polska", "POLSCE": "Polsce", "POLAK": "Polak", "POLACY": "Polacy", "ZŁ": "zł"}
LITERY = "A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż"


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


def zdanie(t):
    """„KAWA NA WYNOS 5 RAZY… ZŁ” → „Kawa na wynos 5 razy… zł”; tytuły pisane normalnie zostają bez zmian."""
    duze = sum(c.isupper() for c in t)
    male = sum(c.islower() for c in t)
    if duze < 2 * max(male, 1):
        return t
    def slowo(m):
        w = m.group(0)
        if w in SKROTY:
            return w
        return NAZWY.get(w, w.lower())
    t = re.sub(f"[{LITERY}]+", slowo, t)
    # wielka litera na początku i po końcu zdania
    return re.sub(rf"(^|[.!?]\s+)([{LITERY}])", lambda m: m.group(1) + m.group(2).upper(), t)


def tytul(surowy, jezyk="pl"):
    """„💛 GDY BUDZISZ SIĘ JUŻ ZMĘCZONA ☀️ 51 MINUT…” → „Gdy budzisz się już zmęczona”.
    Część przed pierwszą emotką / „|” / hasztagiem. ES i DE zostają jak w YouTube (niemieckie rzeczowniki)."""
    t = html.unescape(surowy).strip()
    t = EMOJI.sub(lambda m: "\x00", t).strip("\x00 ")
    t = re.split(r"\x00|\s\|\s|\s#", t)[0]
    t = re.sub(r"#\S+", "", t).strip(" |,")
    return zdanie(t) if jezyk == "pl" else t


def wpisy(xml):
    for e in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        yield (re.search(r"<yt:videoId>(.*?)<", e).group(1),
               re.search(r"<title>(.*?)</title>", e, re.S).group(1),
               re.search(r"<published>(\d{4}-\d\d-\d\d)", e).group(1))


def filmy(k):
    """Najnowsze długie filmy kanału. Najpierw lista UULF (bez shortów), awaryjnie zwykły kanał + test /shorts/."""
    try:
        xml, sprawdz_shorty = pobierz(f"https://www.youtube.com/feeds/videos.xml?playlist_id=UULF{k['id'][2:]}").decode("utf-8"), False
    except Exception:
        xml, sprawdz_shorty = pobierz(f"https://www.youtube.com/feeds/videos.xml?channel_id={k['id']}").decode("utf-8"), True
    wynik = []
    for vid, surowy, dzien in wpisy(xml):
        if k.get("od") and dzien < k["od"]:
            continue
        if re.search(r"#shorts", surowy, re.I) or re.search(r"claude|anthropic|artifact", surowy, re.I):
            continue
        if sprawdz_shorty and kod(f"https://www.youtube.com/shorts/{vid}") == 200:
            continue
        t = tytul(surowy, k.get("jezyk", "pl"))
        if not t:
            continue
        img = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
        if kod(img) != 200:
            img = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        wynik.append({"id": vid, "tytul": t, "img": img})
        if len(wynik) == k["ile"]:
            break
    return wynik


def main():
    wyjscie = sys.argv[sys.argv.index("--wyjscie") + 1] if "--wyjscie" in sys.argv else "kanaly.json"
    try:
        stare = json.load(open(wyjscie, encoding="utf-8"))
    except Exception:
        stare = {}
    nowe, bledy = {}, 0
    for k in KANALY:
        try:
            nowe[k["klucz"]] = filmy(k)
        except Exception as e:
            bledy += 1
            nowe[k["klucz"]] = stare.get(k["klucz"], [])
            print(f"{k['klucz']}: nie mogę odczytać kanału YouTube ({e}), zostaje stara lista")
    zmiana = False
    if bledy < len(KANALY):
        with open(wyjscie, "w", encoding="utf-8") as f:
            json.dump(nowe, f, ensure_ascii=False, indent=1)
        if "--sprawdz" in sys.argv:
            try:
                zmiana = json.loads(pobierz(f"{LIVE}?t={os.getpid()}")) != nowe
            except Exception as e:
                print("nie mogę odczytać opublikowanego kanaly.json:", e)
                zmiana = True
    else:
        print("żaden kanał nie odpowiedział, zostaje stary plik")
    print("kanały:", {k: len(v) for k, v in nowe.items()}, "trzeba publikować:", zmiana)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"kanaly={'true' if zmiana else 'false'}\n")


if __name__ == "__main__":
    main()
