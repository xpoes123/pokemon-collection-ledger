#!/usr/bin/env python3
"""Download every card thumbnail locally and rewrite data.json img paths to
local files, so the deployed site doesn't hotlink tcgdex's CDN (which throttles
browsers loading 200+ images at once). Run after build.py + portfolio.py.

  python3 localize.py   ->   fills img/ and rewrites data.json
"""
import json, os, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "img")


def local_path(base):
    # https://assets.tcgdex.net/en/me/me02/013 -> img/en_me_me02_013.webp
    tail = base.split("assets.tcgdex.net/")[-1].strip("/").replace("/", "_")
    return f"img/{tail}.webp"


def download(base):
    rel = local_path(base)
    dst = os.path.join(HERE, rel)
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return rel
    try:
        with urllib.request.urlopen(base + "/low.webp", timeout=30) as r:
            data = r.read()
        with open(dst, "wb") as f:
            f.write(data)
        return rel
    except Exception as e:
        print("  MISS", base, e)
        return None


def main():
    data = json.load(open(os.path.join(HERE, "data.json")))
    # collect every card dict that has a remote img base
    cards = [c for s in data["sets"] for c in s["cards"]] + data.get("portfolio", [])
    todo = [c for c in cards if c.get("img") and not c["img"].endswith(".webp")]
    os.makedirs(IMG, exist_ok=True)

    print(f"downloading {len(todo)} thumbnails…")
    done = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        for c, rel in zip(todo, ex.map(lambda c: download(c["img"]), todo)):
            if rel:
                c["img"] = rel
                done += 1
    json.dump(data, open(os.path.join(HERE, "data.json"), "w"))
    size = sum(os.path.getsize(os.path.join(IMG, f)) for f in os.listdir(IMG))
    print(f"localized {done}/{len(todo)} images, {size/1e6:.1f} MB in img/")


if __name__ == "__main__":
    main()
