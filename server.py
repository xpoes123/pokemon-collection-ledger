#!/usr/bin/env python3
"""Tiny state API for the Pokémon tracker so stats are shared (everyone sees the
same collection) but only the holder of EDIT_TOKEN can write.

GET  /api/state            -> {"owned": {...}, "packs": {...}}   (public)
PUT  /api/state            -> write state; requires  Authorization: Bearer <EDIT_TOKEN>

State is a single JSON file (STATE_FILE). Single user, low traffic — Flask's
built-in server behind Caddy is plenty. Guardian restarts it if it dies.
"""
import json, os, tempfile
from flask import Flask, request, jsonify

STATE_FILE = os.environ.get("STATE_FILE", os.path.join(os.path.dirname(__file__), "state.json"))
EDIT_TOKEN = os.environ["EDIT_TOKEN"]          # required — no default, fail loud
DEFAULT = {"owned": {}, "packs": {}}

app = Flask(__name__)


def load():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT)


def save(state):
    # atomic write so a crash mid-write can't corrupt the file
    d = os.path.dirname(STATE_FILE) or "."
    fd, tmp = tempfile.mkstemp(dir=d)
    with os.fdopen(fd, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


@app.get("/api/state")
def get_state():
    return jsonify(load())


@app.put("/api/state")
def put_state():
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {EDIT_TOKEN}":
        return jsonify(error="unauthorized"), 401
    body = request.get_json(silent=True)
    if not isinstance(body, dict) or not isinstance(body.get("owned"), dict) \
            or not isinstance(body.get("packs"), dict):
        return jsonify(error="bad body — need {owned:{}, packs:{}}"), 400
    save({"owned": body["owned"], "packs": body["packs"]})
    return jsonify(ok=True)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 7784)), threaded=True)
