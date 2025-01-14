import requests
import logging
import os

from fastapi import FastAPI, HTTPException, Query
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")
HEADERS = {"Authorization": f"Bearer {GENIUS_API_TOKEN}"}

app = FastAPI()


def get_song_language(name: str) -> str | None:
    search_json = _search(name)
    search_status = search_json["meta"]["status"]
    if search_status != 200:
        raise Exception(f"Genius search error. Status code: {search_status}")

    song = _get_song_section(search_json["response"]["hits"])
    song_id = song["id"]
    song_json = _get_song_json(song_id)

    get_info_status = song_json["meta"]["status"]
    if get_info_status != 200:
        raise Exception(
            f"Genius get song info error. Status code: {get_info_status}. Song id: {song_id}"
        )

    language = song_json["response"]["song"].get("language")

    return language


def _search(name: str) -> dict:
    url = "https://api.genius.com/search?q=" + quote_plus(name)
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json()


def _get_song_section(sections: dict) -> dict:
    for sec in sections:
        if sec["type"] == "song" and sec["result"]:
            return sec["result"]

    raise LookupError("Song not found")


def _get_song_json(id: int) -> dict:
    url = f"https://api.genius.com/songs/{id}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json()


@app.get("/")
def home():
    return "Hello from FastAPI on Vercel!"


@app.get("/search")
def search(q: str = Query(..., description="Name of the song")):
    try:
        language = get_song_language(q)
        return {"language": language}
    except LookupError as e:
        logging.exception(f"Song not found: {q}")
        raise HTTPException(status_code=404, detail="Song not found")
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=500, detail=str(e))
