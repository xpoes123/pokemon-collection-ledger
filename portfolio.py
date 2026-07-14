#!/usr/bin/env python3
"""Resolve the collector-portfolio list to real cards (from build.py's cache),
append a 'portfolio' block to data.json. Prints matches for QA."""
import json, glob, re, os
from build import price_for

HERE = os.path.dirname(os.path.abspath(__file__))

# set alias (lowercased substring) -> tcgdex id
ALIAS = {
    "mega evolution": "me01", "mega evolutions": "me01", "mega evoltuion": "me01",
    "mega evoltion": "me01", "mega attack": "me01",
    "twighlight": "sv06", "twilight": "sv06",
    "151": "sv03.5", "ascended": "me02.5", "sachended": "me02.5", "aschended": "me02.5",
    "destined": "sv10", "journey": "sv09",
    "phantasmal": "me02", "white flare": "sv10.5w", "whiteflare": "sv10.5w",
    "black bolt": "sv10.5b", "obsidian": "sv03",
    "stellar": "sv07", "stellera": "sv07",
    "surging": "sv08", "cri": "me04", "chaos rising": "me04", "por": "me03",
    "prismatic": "sv08.5",
}
RHINT = {
    "ir": ["Illustration rare"],
    "sir": ["Special illustration rare"],
    "ur": ["Ultra Rare", "Hyper rare", "Special illustration rare"],
    "double rare": ["Double rare"],
    "mega attack rare": ["Ultra Rare", "Mega Hyper Rare", "Double rare"],
    "": ["Special illustration rare", "Ultra Rare", "Double rare",
         "Illustration rare", "Hyper rare"],
}

# (raw pokemon name, set-alias key, rarity-hint key)
PORTFOLIO = [
    ("Mega Latias ex", "mega evolution", ""),
    ("Eevee", "twilight", "ir"),
    ("Bulbasaur", "151", "ir"),
    ("Psyduck", "ascended", "ir"),
    ("Alakazam ex", "151", "sir"),
    ("Misty's Psyduck", "destined", "ir"),
    ("Salamence ex", "journey", "sir"),
    ("N's Zoroark ex", "journey", ""),
    ("Mega Sharpedo ex", "phantasmal", "sir"),
    ("Meowth", "phantasmal", "ir"),
    ("N's Reshiram", "journey", "ir"),
    ("Trubbish", "white flare", "ir"),
    ("Golurk", "black bolt", "ir"),
    ("Mr. Mime", "151", "ir"),
    ("Infernape", "twilight", "ir"),
    ("Banette", "ascended", "ir"),
    ("Cynthia's Spiritomb", "ascended", "ir"),
    ("Team Rocket's Dugtrio", "ascended", "ir"),
    ("Dreepy", "ascended", "ir"),
    ("Basculin", "white flare", "ir"),
    ("Cryogonal", "black bolt", "ir"),
    ("Ferroseed", "whiteflare", "ir"),
    ("Larvitar", "obsidian", "ir"),
    ("Lillie's Ribombee", "journey", "ir"),
    ("Ledian", "stellar", "ir"),
    ("Wigglytuff", "phantasmal", "ir"),
    ("Dawn", "phantasmal", "ur"),
    ("Vivillon", "surging", "ir"),
    ("Mega Scrafty ex", "ascended", "mega attack rare"),
    ("Hop's Wooloo", "journey", "ir"),
    ("Flygon", "phantasmal", "ir"),
    ("Mega Charizard ex", "phantasmal", "double rare"),
    ("Hydrapple ex", "stellar", "ur"),
    ("Zekrom ex", "black bolt", "ur"),
    ("Dewgong", "phantasmal", "ir"),
    ("Paldean Wooper", "phantasmal", "ir"),
    ("Beedrill ex", "cri", "ur"),
    ("Zacian", "phantasmal", "ir"),
    ("Pikachu ex", "surging", ""),
    ("Yamper", "phantasmal", "ir"),
    ("Helioptile", "mega evolution", "ir"),
    ("Gumshoos", "mega evolution", "ir"),
    ("Shedinja", "mega evolution", "ir"),
    ("Absol ex", "obsidian", ""),
    ("Bruxish", "surging", "ir"),
    ("Mega Gengar ex", "phantasmal", "double rare"),
    ("Mega Lopunny ex", "phantasmal", "ur"),
    ("Ludicolo", "phantasmal", "ir"),
    ("Ambipom", "phantasmal", "ir"),
    ("Toxtricity", "phantasmal", "ir"),
    ("Nymble", "phantasmal", "ir"),
    ("Serperior ex", "black bolt", "ur"),
    ("Orthworm ex", "stellar", "ur"),
    ("Mega Greninja ex", "cri", "double rare"),
]


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).split()


# load all cached card details grouped by set id
BYSET = {}
for f in glob.glob(os.path.join(HERE, "cache", "*.json")):
    d = json.load(open(f))
    BYSET.setdefault(d["set"]["id"], []).append(d)


def resolve(name, setkey, hint):
    sid = ALIAS[setkey]
    want = set(norm(name))
    cands = []
    for c in BYSET.get(sid, []):
        cn = set(norm(c["name"]))
        # all query tokens present in card name (handles "Mega X ex", "N's X")
        if want <= cn:
            cands.append(c)
    if not cands:
        # looser: main pokemon token (last non-ex word) in name
        core = [t for t in norm(name) if t not in ("mega", "ex")]
        cands = [c for c in BYSET.get(sid, [])
                 if core and core[-1] in norm(c["name"])]
    ranks = RHINT[hint]
    cands.sort(key=lambda c: ranks.index(c["rarity"]) if c["rarity"] in ranks else 99)
    return sid, cands


rows, out = [], []
for name, setkey, hint in PORTFOLIO:
    sid, cands = resolve(name, setkey, hint)
    if not cands:
        rows.append((name, sid, hint, "!! NO MATCH", "", 0))
        continue
    best = cands[0]
    n_ok = sum(1 for c in cands if c["rarity"] in RHINT[hint])
    rows.append((name, sid, hint, best["name"], best["rarity"],
                 len([c for c in cands])))
    out.append({"query": name, "id": sid, "n": best["localId"],
                "name": best["name"], "rarity": best["rarity"],
                "img": best.get("image"),
                "price": price_for("ex", best.get("pricing"))})

print(f"{'QUERY':26} {'SET':8} {'HINT':16} -> {'MATCHED':26} {'RARITY':26} cand")
for r in rows:
    flag = "  " if r[3] != "!! NO MATCH" and (r[2] == "" or r[4] in RHINT.get(r[2], [])) else "??"
    print(f"{flag}{r[0]:26.26} {r[1]:8} {r[2]:16.16} -> {r[3]:26.26} {r[4]:26.26} {r[5]}")

# Graded / vintage singles outside the 15 tracked sets — hand-entered.
# Prices are ROUGH ballparks for the given grade; edit freely.
MANUAL = [
    # graded slabs
    {"name": "Eevee", "setlabel": "Prismatic Evolutions ETB", "grade": "PSA 10",
     "img": "https://assets.tcgdex.net/en/sv/svp/173", "price": 160},
    {"name": "Mewtwo", "setlabel": "Base Set · 1st Edition", "grade": "PSA 7",
     "img": "https://assets.tcgdex.net/en/base/base1/10", "price": 111},
    {"name": "Mew", "setlabel": "XY Evolutions", "grade": "PSA 9",
     "img": "https://assets.tcgdex.net/en/xy/xy12/53", "price": 86},
    {"name": "Shadow Rider Calyrex V", "setlabel": "Chilling Reign", "grade": "PSA 10",
     "img": "https://assets.tcgdex.net/en/swsh/swsh6/172", "price": 78},
    {"name": "Mega Dragonite ex", "setlabel": "Ascended Heroes", "grade": "PSA 9",
     "img": "https://assets.tcgdex.net/en/sv/me02.5/271", "price": 76},
    {"name": "Raichu-GX", "setlabel": "Secret Rare", "grade": "PSA 9",
     "img": None, "price": 73},
    # ungraded singles / promos
    {"name": "Gengar ex", "setlabel": "Temporal Forces", "grade": "SIR",
     "img": "https://assets.tcgdex.net/en/sv/sv05/193", "price": 64},
    {"name": "Deerling", "setlabel": "Temporal Forces", "grade": "IR",
     "img": "https://assets.tcgdex.net/en/sv/sv05/165", "price": 45},
    {"name": "Umbreon ex", "setlabel": "SVP Promo", "grade": "Promo",
     "img": None, "price": 42},
    {"name": "Espeon ex", "setlabel": "SVP Promo", "grade": "Promo",
     "img": None, "price": 25},
    {"name": "N's Zekrom", "setlabel": "Mega Evolution Promo", "grade": "Promo",
     "img": None, "price": 10},
    {"name": "Oricorio ex", "setlabel": "Mega Evolution Promo", "grade": "Promo",
     "img": None, "price": 1},
    {"name": "Mega Charizard X ex", "setlabel": "Mega Evolution Promo", "grade": "Promo",
     "img": None, "price": 40},
    {"name": "Mega Charizard Y ex", "setlabel": "Mega Evolution Promo", "grade": "Promo",
     "img": None, "price": 40},
]
for m in MANUAL:
    out.append({"query": m["name"], "id": m["setlabel"], "setlabel": m["setlabel"],
                "n": "", "name": m["name"], "rarity": m["grade"],
                "img": m["img"], "price": m["price"], "graded": True})
print(f"+ {len(MANUAL)} graded/manual cards")

# merge into data.json under 'portfolio'
data = json.load(open(os.path.join(HERE, "data.json")))
data["portfolio"] = out
json.dump(data, open(os.path.join(HERE, "data.json"), "w"))
print(f"\n{len(out)}/{len(PORTFOLIO)} resolved, written to data.json")
