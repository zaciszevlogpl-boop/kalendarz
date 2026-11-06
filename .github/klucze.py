"""Robot kalendarza adwentowego Zacisza: wystawia klucze okienek, których dzień już nadszedł (czas polski).

Klucze bierze z sekretu repo KLUCZE (JSON {"1": "...", ..., "24": "..."}), zapisuje klucze.json
tylko z okienkami <= dziś. Okienko N otwiera się N grudnia o północy w Polsce, nigdy wcześniej.
Test lokalny: KLUCZE="$(cat _klucze_PRYWATNE.json)" python3 klucze.py --dzis 2026-12-05T00:03
"""
import datetime, json, os, sys, urllib.request
from zoneinfo import ZoneInfo

ROK = 2026
URL = "https://www.zaciszevlog.pl/klucze.json"
PL = ZoneInfo("Europe/Warsaw")

teraz = datetime.datetime.now(PL)
if "--dzis" in sys.argv:
    teraz = datetime.datetime.fromisoformat(sys.argv[sys.argv.index("--dzis") + 1]).replace(tzinfo=PL)
K = json.loads(os.environ["KLUCZE"])
if sorted(K, key=int) != [str(n) for n in range(1, 25)]:
    sys.exit("Sekret KLUCZE nie ma 24 kluczy")
dzis = teraz.date()
wolno = [n for n in range(1, 25) if datetime.date(ROK, 12, n) <= dzis]
nowe = {str(n): K[str(n)] for n in wolno}
with open("klucze.json", "w") as f:
    json.dump(nowe, f)

zmiana = True
if "--dzis" not in sys.argv:
    try:
        with urllib.request.urlopen(f"{URL}?t={teraz.timestamp():.0f}", timeout=20) as r:
            zmiana = json.load(r) != nowe
    except Exception as e:
        print("nie mogę odczytać opublikowanego klucze.json:", e)
print(f"teraz w Polsce: {teraz:%d.%m.%Y %H:%M}, wystawione okienka: {wolno or 'żadne'}, trzeba publikować: {zmiana}")
if os.environ.get("GITHUB_OUTPUT"):
    with open(os.environ["GITHUB_OUTPUT"], "a") as f:
        f.write(f"zmiana={'true' if zmiana else 'false'}\n")
