"""Self-check: python test_render.py"""
import io

from PIL import Image, ImageDraw

import render as r

photo_bytes = io.BytesIO()
_p = Image.new("RGB", (4000, 3000), "#3355aa")
ImageDraw.Draw(_p).ellipse([1600, 700, 2400, 1500], fill="#ffcc88")
_p.save(photo_bytes, "JPEG")
PHOTO = r.prepare_photo(photo_bytes.getvalue())

# 1. every stored title stays on one line inside a block that clears the beach tile at x=1334
assert len(r.TITLES) == len(set(r.TITLES)), "duplicate titles"
for t in r.TITLES:
    assert len(t) <= 24, f"title too long: {t}"
    f, size = r.fit(t.upper(), r.BRICOLAGE, 700, 32, -0.01, 660, 22)
    assert size == 32, f"title had to shrink: {t}"
    block_w = max(348, r.measure(t.upper(), f, -0.01 * size) / r.S + 40)
    assert 576 + block_w < 1334, f"title block hits the beach tile: {t}"

# 2. the variable font axes actually applied — a silent fallback would render every weight the same
w600 = r.measure("HAMBURG", r.font(r.BRICOLAGE, 100, 600), 0)
w800 = r.measure("HAMBURG", r.font(r.BRICOLAGE, 100, 800), 0)
assert w800 > w600, "Bricolage weight axis not applied"
ink = []
for weight in (500, 700):
    im = Image.new("L", (400, 200), 0)
    ImageDraw.Draw(im).text((10, 10), "HM", font=r.font(r.JBMONO, 60, weight), fill=255)
    ink.append(sum(im.histogram()[129:]))
assert ink[1] > ink[0], "JetBrains Mono weight axis not applied"

# 3. a long name shrinks into its 718px box and the card comes out at artboard size
for name in ["Li", "Siddharth", "Priyadarshini Kulkarni", "Bartholomew Christopher Wickramasinghe"]:
    lines, size = r.name_lines(name)
    f = r.font(r.BRICOLAGE, size, 800)
    widest = max(r.measure(l, f, -0.05 * size) for l in lines) / r.S
    assert widest <= 718, f"name overflows: {name} -> {widest:.0f}px"
    assert len(lines) <= 2, f"name wrapped past 2 lines: {name}"
card, _ = r.make_card(PHOTO, name, "Rust, ZK, Inference", "Ghumot", "The Latency Monk")
assert card.size == (1620, 1020), card.size

# 4. hashtag is right-aligned to 1543 and clears the pink dot at cx=1359
hw = r.measure(r.HASHTAG, r.font(r.JBMONO, 19, 700), 2.66) / r.S
assert r.HASHTAG == "#FrameInGoa", "wrong hashtag — the submission is invalid without #FrameInGoa"
assert 1543 - hw > 1365, f"hashtag overlaps the dot (left edge {1543 - hw:.0f})"

print("ok — 4 checks passed")
