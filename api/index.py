import aiohttp
import logging
import os

from fastapi import FastAPI, HTTPException, Query
from urllib.parse import quote_plus
from dotenv import load_dotenv


load_dotenv()

AIOHTTP_SESSION = None
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN")

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    global AIOHTTP_SESSION
    if AIOHTTP_SESSION is None:
        AIOHTTP_SESSION = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {GENIUS_API_TOKEN}"
            }
        )


@app.on_event("shutdown")
async def shutdown_event():
    global AIOHTTP_SESSION
    if AIOHTTP_SESSION:
        await AIOHTTP_SESSION.close()


async def get_song_language(name: str) -> str | None:
    search_json = await _search(name)
    search_status = search_json["meta"]["status"]
    if search_status != 200:
        raise Exception(f"Genius search error. Status code: {search_status}")

    song = _get_song_section(search_json["response"]["hits"])
    song_id = song["id"]
    song_json = await _get_song_json(song_id)

    get_info_status = song_json["meta"]["status"]
    if get_info_status != 200:
        raise Exception(
            f"Genius get song info error. Status code: {get_info_status}. Song id: {song_id}"
        )

    language = song_json["response"]["song"].get("language")

    return language


async def _search(name: str) -> dict:
    url = "https://api.genius.com/search?q=" + quote_plus(name)
    async with AIOHTTP_SESSION.get(url) as res:
        res.raise_for_status()
        return await res.json(content_type=None)


def _get_song_section(sections: dict) -> dict:
    for sec in sections:
        if sec["type"] == "song" and sec["result"]:
            return sec["result"]

    raise LookupError("Song not found")


async def _get_song_json(id: int) -> str:
    url = f"https://api.genius.com/songs/{id}"
    async with AIOHTTP_SESSION.get(url) as res:
        res.raise_for_status()
        return await res.json(content_type=None)


@app.get("/")
async def home():
    return "Hello from FastAPI on Vercel!"


@app.get("/search")
async def search(q: str = Query(..., description="Name of the song")):
    try:
        language = await get_song_language(q)
        return {"language": language}
    except LookupError as e:
        logging.exception(f"Song not found: {q}")
        raise HTTPException(status_code=404, detail="Song not found")
    except Exception as e:
        logging.exception(e)
        raise HTTPException(status_code=500, detail="Internal Server Error")
