# HH Goa 2026 — Builder ID Card Generator

**Live: https://hhgoa-task1.onrender.com**

Upload a photo, fill four fields, get a branded 1620×1020 Builder ID card to download and post
on X with **#FrameInGoa**. Track is AI × Crypto for everyone.

## Run

```sh
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python test_render.py          # self-check
.venv/bin/uvicorn app:app --port 8000    # http://localhost:8000
```

Docker: `docker build -t hhgoa . && docker run -p 8000:8000 hhgoa`

Share links and `og:image` URLs are absolute and default to the Render host above, because X fetches
the preview image over the public internet. Set `PUBLIC_BASE_URL` to point them somewhere else.

## How it works

`assets/static.png` is the finished 3240×2040 design layer; `assets/spec.json` is the contract for
what goes on top. `render.py` composites the photo and the variable text at 2× and downscales to
1620×1020, so small type stays clean.

| Field | Source |
|---|---|
| Name, stack, team | user |
| Builder title | random from `titles.json` (248 entries), rerollable |
| Track | always `AI × Crypto` |
| Check-in, builder number | generated at render time |

Text fitting: every field measures itself and steps the font size down until it fits its box; the
name breaks to a second line past 18 characters and collapses to `initial + surname` past 30. The
pink title block is baked into the PNG at 348px, so it is redrawn whenever the title needs it wider.

Two corrections to `assets/spec.json`, both deliberate:
- the hashtag is `#FrameInGoa`, not `#FramedInGoa` (the brief invalidates posts with the wrong tag);
- the spec says the pink hashtag dot is baked into the static layer — it isn't, so `render.py`
  draws it.

## Endpoints

| | |
|---|---|
| `POST /api/generate` | multipart `photo, name, stack, team` → `{id, title, image, share, tweet}` |
| `POST /api/reroll/{id}` | new title on the cached crop, no re-upload |
| `GET /i/{id}.png` | the card |
| `GET /c/{id}` | share page carrying the `og:image` X previews |
