#!/usr/bin/env python3
"""Build data.json for the Pokemon card tracker from the master-set xlsx + tcgdex.

Run: python3 build.py [path/to/Pokemon Master Sets.xlsx]
Card data is cached under cache/ so re-runs (e.g. after editing the sheet) are fast.
"""
import json, sys, os, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
XLSX = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/Downloads/Pokemon Master Sets.xlsx")

# sheet name -> tcgdex set id
SETS = {
    "151": "sv03.5", "Obsidian Flames": "sv03", "twm": "sv06",
    "Surging Sparks": "sv08", "Mega Evolutions": "me01", "Destined Rivals": "sv10",
    "SCR": "sv07", "Phantasmal Flames": "me02", "Journey Together": "sv09",
    "CRI": "me04", "POR": "me03", "PRE": "sv08.5", "BLK": "sv10.5b",
    "WHT": "sv10.5w", "Ascended Heros": "me02.5",
}
# order the sets appear on the page (newest-ish / your call — just the dict order)
ORDER = list(SETS.keys())

# spreadsheet column header -> variant key. Unknown headers pass through lowercased.
COLMAP = {"normal": "normal", "reverse": "reverse", "ex": "ex",
          "poke": "poke", "ultra": "ultra", "master": "master", "cool": "cool"}
# variants we can verify per-card from tcgdex; others are "special" (heuristic availability)
STANDARD = {"normal", "reverse", "ex"}


def fetch(url):
    for _ in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass
    raise RuntimeError("failed: " + url)


def card_detail(setid, localid):
    """tcgdex card detail, cached to disk."""
    fn = os.path.join(CACHE, f"{setid}-{localid}.json")
    if os.path.exists(fn):
        return json.load(open(fn))
    d = fetch(f"https://api.tcgdex.net/v2/en/cards/{setid}-{localid}")
    if d is not None:
        json.dump(d, open(fn, "w"))
    return d


def price_for(variant, pricing):
    """Rough USD market price for a variant. tcgplayer (USD) first, else cardmarket EUR*1.08."""
    tcg = (pricing or {}).get("tcgplayer") or {}
    cm = (pricing or {}).get("cardmarket") or {}

    def tp(key):
        v = tcg.get(key)
        return v.get("marketPrice") if isinstance(v, dict) else None
    if variant == "reverse":
        p = tp("reverse-holofoil")
    elif variant == "ex":
        p = tp("holofoil") or tp("normal")
    elif variant == "normal":
        p = tp("normal") or tp("holofoil")
    else:  # special reverse patterns (poke/master/etc) — approximate
        p = tp("reverse-holofoil") or tp("normal") or tp("holofoil")
    if p is None and cm:  # ponytail: flat 1.08 EUR->USD, good enough for a rough total
        eur = (cm.get("avg-holo") if variant in ("ex", "reverse") else None) or cm.get("avg")
        if eur:
            p = round(eur * 1.08, 2)
    return round(p, 2) if p else None


def read_sheet_owned(ws_rows):
    """rows -> {localId(int): {variant_key: True}} from checkmarks, + column keys used."""
    header = [str(c).strip().lower() if c else "" for c in ws_rows[0]]
    cols = {i: COLMAP.get(h, h) for i, h in enumerate(header) if i > 0 and h}
    owned = {}
    for row in ws_rows[1:]:
        if not row or row[0] is None:
            continue
        try:
            cid = int(float(row[0]))
        except (ValueError, TypeError):
            continue
        marks = {cols[i]: True for i in range(1, len(row))
                 if i in cols and row[i] not in (None, "", " ")}
        if marks:
            owned[cid] = marks
    return owned, list(cols.values())


def main():
    import openpyxl
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    out = []
    for sheet in ORDER:
        setid = SETS[sheet]
        rows = list(wb[sheet].iter_rows(values_only=True))
        owned, sheet_cols = read_sheet_owned(rows)
        special_cols = [c for c in sheet_cols if c not in STANDARD]

        setmeta = fetch(f"https://api.tcgdex.net/v2/en/sets/{setid}")
        briefs = setmeta["cards"]
        print(f"{sheet:20s} {setid:8s} {len(briefs)} cards, "
              f"{sum(len(v) for v in owned.values())} owned marks", flush=True)

        details = {}
        with ThreadPoolExecutor(max_workers=16) as ex:
            for b, d in zip(briefs, ex.map(
                    lambda b: card_detail(setid, b["localId"]), briefs)):
                details[b["localId"]] = d

        cards = []
        for b in briefs:
            lid = b["localId"]
            try:
                n = int(lid)
            except ValueError:
                n = None  # non-numeric promo-ish id; still show, just won't seed
            d = details.get(lid) or {}
            name = d.get("name") or b.get("name") or lid
            rarity = d.get("rarity", "")
            tv = d.get("variants", {}) or {}
            is_ex = name.lower().endswith(" ex")

            avail = []
            if not is_ex:
                avail.append("normal")            # ex cards' only print is the ex holo
            if tv.get("reverse"):
                avail.append("reverse")
            if is_ex:
                avail.append("ex")
            # special reverse patterns (Poke/Master Ball etc): non-ex cards that have a reverse
            for sc in special_cols:
                if not is_ex and tv.get("reverse"):
                    avail.append(sc)

            seed = owned.get(n, {}) if n is not None else {}
            # keep a seed even if we didn't mark that variant available (sheet wins)
            for k in seed:
                if k not in avail:
                    avail.append(k)

            prices = {v: price_for(v, d.get("pricing")) for v in avail}
            cards.append({
                "n": lid,
                "name": name,
                "rarity": rarity,
                "img": b.get("image"),   # append /low.webp on the page
                "variants": avail,
                "owned": {k: True for k in seed},
                "prices": prices,
            })

        out.append({"sheet": sheet, "id": setid, "name": setmeta["name"],
                    "cards": cards})

    json.dump({"sets": out}, open(os.path.join(HERE, "data.json"), "w"))
    tot = sum(len(s["cards"]) for s in out)
    print(f"\nwrote data.json — {len(out)} sets, {tot} cards")


if __name__ == "__main__":
    main()
