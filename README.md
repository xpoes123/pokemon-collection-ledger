# Pokémon Collection Ledger

A single static page that turns a spreadsheet of your Pokémon TCG master sets into
a browsable collection tracker: card art, per-variant checkboxes, set completion
bars, and rough market values (how much you own, how much to finish each set).

**Live demo:** https://pokemon.djiang.xyz

- 🖼️ Real card names + art for every set (via the free [TCGdex](https://tcgdex.dev) API)
- ✅ Track each variant separately (Normal / Reverse / EX + special reverse patterns)
- 💰 Rough tcgplayer market prices — collection worth & cost-to-finish per set
- ⭐ A separate "chase portfolio" view for your illustration rares / SIRs / URs
- 💾 No backend. Edits save to your browser's `localStorage`, seeded from the sheet

There's nothing to run to *use* it — it's one `index.html` + a generated
`data.json`. You only run the build scripts to regenerate `data.json` from your
own spreadsheet.

---

## How it works

1. `build.py` reads your `.xlsx`, and for each set pulls the full card list from
   TCGdex (name, art, rarity, which variants physically exist, and pricing),
   caching every card under `cache/` so re-runs take seconds.
2. It writes `data.json` — every card with its available variants, your owned
   state (seeded from the sheet's checkmarks), and per-variant USD prices.
3. `index.html` loads `data.json` and renders everything. Clicking a variant
   badge toggles owned and saves it locally.
4. `portfolio.py` (optional) resolves a hand-written list of chase cards to real
   cards and appends them as a `portfolio` block in `data.json`.

## Use it yourself

### 1. Prepare a spreadsheet

One **sheet per set**. First row is a header; the first column is the card
number, and each following column is a variant you want to track:

| ID | Normal | Reverse | EX |
|----|--------|---------|----|
| 1  | ✔      |         |    |
| 2  | ✔      | ✔       |    |
| 3  |        |         | ✔  |

- Any non-empty cell = you own that variant. (The author's sheet uses a
  Wingdings check that reads as `l` — any mark works.)
- Column headers map to variant keys: `Normal`, `Reverse`, `EX`, and the special
  ones `poke` / `ultra` / `master` (Prismatic Evolutions) and `cool` (Black Bolt).
  Unknown headers are passed through as their own toggleable badge.
- Numbers past a set's real card count are simply ignored.

### 2. Point each sheet at a TCGdex set

Edit the `SETS` dict in `build.py` — map **your sheet name → the TCGdex set id**:

```python
SETS = {
    "151": "sv03.5",
    "Surging Sparks": "sv08",
    "Prismatic Evolutions": "sv08.5",
    # ...
}
```

Find set ids by browsing the API:
`https://api.tcgdex.net/v2/en/sets` (id + name for every set).

### 3. Build and open

```bash
pip install -r requirements.txt
python3 build.py "path/to/Your Master Sets.xlsx"   # writes data.json
python3 portfolio.py                                # optional: chase-card view
```

Then serve the folder (the page fetches `data.json`, so `file://` won't work):

```bash
python3 -m http.server 8000    # then open http://localhost:8000
```

Deploy anywhere that serves static files (GitHub Pages, Netlify, an nginx/Caddy
root, etc.) — just upload `index.html` + `data.json`.

### Chase portfolio (optional)

Edit the `PORTFOLIO` list in `portfolio.py` — one tuple per card:
`("Card Name", "set-alias", "rarity-hint")`, where the alias matches a key in
that file's `ALIAS` dict and the hint is one of `ir`, `sir`, `ur`,
`double rare`, `mega attack rare`, or `""`. Re-run `python3 portfolio.py`; it
prints each match so you can eyeball it.

## Notes & limitations

- **Prices are rough.** tcgplayer market price per variant where available, else
  a flat EUR→USD conversion of the cardmarket average. Good for ballpark totals,
  not for insurance.
- **"Cost to finish"** counts *every* card in the set, including secret rares and
  illustration rares — that's why the number is steep.
- **Edits are per-browser.** `localStorage` doesn't sync across devices and
  resets if you clear site data. Your spreadsheet stays the source of truth;
  re-run `build.py` to re-seed.
- Special reverse-pattern availability (Poké/Master Ball, etc.) uses a heuristic;
  the spreadsheet's own checks always win.

## Credits

Card data, art, and pricing from [TCGdex](https://tcgdex.dev). Not affiliated
with Nintendo / The Pokémon Company.
