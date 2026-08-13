import html
import json
import os
import random
import uuid
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import render

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
MAX_UPLOAD = 10 * 1024 * 1024

app = FastAPI(title="HH Goa 2026 Builder ID")


def base_url(request: Request):
    return os.environ.get("PUBLIC_BASE_URL", str(request.base_url)).rstrip("/")


def payload(card_id, meta, request):
    base = base_url(request)
    caption = (f"{meta['name']} · {render.TRACK} · {meta['title']}\n"
               f"My Hacker House Goa 2026 builder ID 🌴\n\n{render.HASHTAG}")
    share = f"{base}/c/{card_id}"
    return {
        "id": card_id,
        "title": meta["title"],
        "image": f"/i/{card_id}.png",
        "share": share,
        "tweet": f"https://twitter.com/intent/tweet?text={quote(caption)}&url={quote(share)}",
    }


def build(card_id, meta, photo):
    card = render.render(photo, meta["name"], meta["stack"], meta["team"], meta["title"],
                         number=meta["number"], check_in=meta["check_in"])
    card.save(os.path.join(DATA, f"{card_id}.png"))
    json.dump(meta, open(os.path.join(DATA, f"{card_id}.json"), "w"))


def clean(value, field, limit, default=None):
    value = " ".join((value or "").split())
    if not value:
        if default is None:
            raise HTTPException(400, f"{field} is required")
        return default
    if len(value) > limit:
        raise HTTPException(400, f"{field} must be {limit} characters or fewer")
    return value


@app.post("/api/generate")
async def generate(request: Request, photo: UploadFile = File(...), name: str = Form(...),
                   stack: str = Form(...), team: str = Form("")):
    data = await photo.read()
    if not data:
        raise HTTPException(400, "No photo received")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(400, "Photo is larger than 10MB")
    try:
        cropped = render.prepare_photo(data)
    except Exception:
        raise HTTPException(400, "Could not read that image — try a JPG, PNG or HEIC")

    meta = {
        "name": clean(name, "Name", 48),
        "stack": clean(stack, "Stack", 64),
        "team": clean(team, "Team", 22, default="Solo"),
        "title": render.pick_title(),
        "number": random.randint(1, 247),
        "check_in": render.now_check_in(),
    }
    card_id = uuid.uuid4().hex[:12]
    cropped.save(os.path.join(DATA, f"{card_id}.src.jpg"), quality=92)
    build(card_id, meta, cropped)
    return payload(card_id, meta, request)


@app.post("/api/reroll/{card_id}")
def reroll(card_id: str, request: Request):
    """New title on the cached crop — keeps a phone off the upload path just to change a joke."""
    src = os.path.join(DATA, f"{secure(card_id)}.src.jpg")
    meta_path = os.path.join(DATA, f"{secure(card_id)}.json")
    if not (os.path.exists(src) and os.path.exists(meta_path)):
        raise HTTPException(404, "Card expired — generate a new one")
    meta = json.load(open(meta_path))
    meta["title"] = render.pick_title(exclude=meta["title"])
    new_id = uuid.uuid4().hex[:12]
    photo = Image.open(src)
    photo.save(os.path.join(DATA, f"{new_id}.src.jpg"), quality=92)
    build(new_id, meta, photo)
    return payload(new_id, meta, request)


def secure(card_id: str):
    if not card_id.isalnum():
        raise HTTPException(404, "Not found")
    return card_id


@app.get("/i/{card_id}.png")
def image(card_id: str):
    path = os.path.join(DATA, f"{secure(card_id)}.png")
    if not os.path.exists(path):
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="image/png",
                        headers={"Cache-Control": "public, max-age=31536000, immutable"})


@app.get("/c/{card_id}", response_class=HTMLResponse)
def share_page(card_id: str, request: Request):
    """Landing page for the shared link — its og:image is what X renders in the post preview."""
    meta_path = os.path.join(DATA, f"{secure(card_id)}.json")
    if not os.path.exists(meta_path):
        raise HTTPException(404, "Not found")
    meta = json.load(open(meta_path))
    base = base_url(request)
    img = f"{base}/i/{card_id}.png"
    title = html.escape(f"{meta['name']} — {meta['title']} · Hacker House Goa 2026", quote=True)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="Builder ID · {render.TRACK} · 28–31 Oct 2026 · {render.HASHTAG}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1620">
<meta property="og:image:height" content="1020">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:image" content="{img}">
<style>body{{margin:0;background:#12100E;color:#FFF4DC;font:16px/1.5 system-ui,sans-serif;
text-align:center;padding:24px}}img{{max-width:100%;border-radius:12px}}
a{{color:#FFD62B;display:inline-block;margin-top:20px}}</style></head>
<body><img src="{img}" alt="{title}"><br><a href="{base}/">Make your own Builder ID →</a></body></html>"""


app.mount("/", StaticFiles(directory=os.path.join(HERE, "static"), html=True), name="static")
