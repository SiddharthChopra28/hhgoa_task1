"""Composites a HH Goa 2026 Builder ID card from the supplied static layer + variable text.

Coordinates below are artboard px (1620x1020) straight out of assets/spec.json; everything is
drawn at 2x on the 3240x2040 static PNG and downscaled at the end, so small text stays clean.
"""
import io
import json
import os
import random
from datetime import datetime
from zoneinfo import ZoneInfo

import pillow_heif
from PIL import Image, ImageDraw, ImageFont, ImageOps

pillow_heif.register_heif_opener()  # iPhone .heic uploads

HERE = os.path.dirname(os.path.abspath(__file__))
S = 2  # static layer is 2x the artboard
W, H = 1620, 1020

GREEN = "#0E7A4E"
YELLOW = "#FFD62B"
PINK = "#FF4E8A"
COCONUT = "#FFF4DC"
INK = "#12100E"
# coconut @ 70% over the green identity panel, pre-blended (drawing alpha ink on RGB does not blend)
COCONUT_70_ON_GREEN = (183, 207, 177)

BRICOLAGE = os.path.join(HERE, "assets/fonts/bricolage.ttf")
JBMONO = os.path.join(HERE, "assets/fonts/jbmono.ttf")

TITLES = json.load(open(os.path.join(HERE, "titles.json")))
TRACK = "AI × Crypto"
HASHTAG = "#FrameInGoa"

_static = None


def static_layer():
    global _static
    if _static is None:
        _static = Image.open(os.path.join(HERE, "assets/static.png")).convert("RGB")
    return _static


def font(path, size, weight):
    """Both fonts are variable. Bricolage axis order is opsz, wght, wdth — not what you'd guess."""
    f = ImageFont.truetype(path, round(size * S))
    if path == BRICOLAGE:
        f.set_variation_by_axes([min(96, max(12, size)), weight, 100])
    else:
        f.set_variation_by_axes([weight])
    return f


def measure(text, f, ls):
    """Width in device px of `text` drawn with `ls` artboard px of tracking."""
    if not text:
        return 0.0
    return sum(f.getlength(c) for c in text) + ls * S * (len(text) - 1)


def tracked(d, x, baseline, text, f, ls, fill, align="left"):
    """Draw with letter-spacing (Pillow has none). x is the left, right or centre edge per `align`.

    ponytail: per-char drawing drops kerning pairs. Every tracked field here is uppercase or mono,
    where kerning is negligible; revisit if a specific pair ever looks wrong.
    """
    w = measure(text, f, ls)
    x = x * S
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    for c in text:
        d.text((x, baseline * S), c, font=f, fill=fill, anchor="ls")
        x += f.getlength(c) + ls * S
    return w


def baseline_of(y, size):
    """Spec: y is the top of the text box, baseline sits at y + fontSize * 0.8."""
    return y + size * 0.8


def band_baseline(text, f, band_y, band_h):
    """Baseline that centres `text` in a coloured band by its real ink extents.

    The spec's y + 0.8 * size rule is a rough approximation and leaves everything sitting a few px
    high inside its bar — most visibly the mixed-case hashtag in the footer.
    """
    _, top, _, bottom = f.getbbox(text, anchor="ls")
    return band_y + band_h / 2 - (top + bottom) / 2 / S


def fit(text, path, weight, size, em_ls, max_w, min_size):
    """Step the font size down until the tracked text fits `max_w` artboard px."""
    while size > min_size:
        f = font(path, size, weight)
        if measure(text, f, em_ls * size) <= max_w * S:
            return f, size
        size -= 2
    return font(path, size, weight), size


def ellipsize(text, f, em_ls, size, max_w):
    """Last resort after `fit` has already bottomed out on font size."""
    if measure(text, f, em_ls * size) <= max_w * S:
        return text
    while text and measure(text + "…", f, em_ls * size) > max_w * S:
        text = text[:-1]
    return text + "…"


def prepare_photo(data):
    """EXIF-rotate, then cover-crop to the 432x432 square. Handles portrait/landscape/off-centre."""
    img = Image.open(io.BytesIO(data) if isinstance(data, bytes) else data)
    img = ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.fit(img, (432 * S, 432 * S), Image.LANCZOS, centering=(0.5, 0.42))


def name_lines(name):
    """Spec size steps by length, with a measured shrink after — the steps are estimates and an
    8-char name at 150 already crowds the 718px box."""
    name = " ".join(name.split()).upper()
    if len(name) > 30:
        parts = name.split()
        if len(parts) > 1:
            name = parts[0][0] + ". " + parts[-1]
        else:
            name = name[:30]
    size = 150 if len(name) <= 8 else 96 if len(name) <= 18 else 72

    lines = [name]
    if len(name) > 18 and " " in name:  # break at the space nearest the middle
        spaces = [i for i, c in enumerate(name) if c == " "]
        i = min(spaces, key=lambda i: abs(i - len(name) / 2))
        lines = [name[:i], name[i + 1:]]

    while size > 40:
        f = font(BRICOLAGE, size, 800)
        if max(measure(l, f, -0.05 * size) for l in lines) <= 718 * S:
            break
        size -= 4
    return lines, size


def pick_title(exclude=None):
    choices = [t for t in TITLES if t != exclude] or TITLES
    return random.choice(choices)


def render(photo, name, stack, team, title, number=None, check_in=None):
    """Returns the finished 1620x1020 card as a PIL Image."""
    card = static_layer().copy()
    d = ImageDraw.Draw(card)

    # --- photo (cream frame + green stroke are already baked into the static layer) ---
    mask = Image.new("L", (432 * S, 432 * S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 432 * S - 1, 432 * S - 1], 22 * S, fill=255)
    card.paste(photo, (44 * S, 228 * S), mask)

    # --- stack: max 3 items, one line, never wraps ---
    items = [i.strip().upper() for i in stack.replace("·", ",").split(",") if i.strip()][:3]
    text = " · ".join(items)
    f, size = fit(text, JBMONO, 700, 20, 0.26, 718, 13)
    tracked(d, 576, baseline_of(204, 20), text, f, 0.26 * size, INK)

    # --- builder name ---
    lines, size = name_lines(name)
    f = font(BRICOLAGE, size, 800)
    for i, line in enumerate(lines):
        tracked(d, 576, baseline_of(250 + i * size * 0.9, size), line, f, -0.05 * size, GREEN)

    # --- builder title ---
    # The pink block is baked into the static layer at 348 wide. Paint the ground colour back over
    # that footprint first, then draw the block at the width this title actually needs — so a short
    # title gets a tight block instead of pink trailing off to the right of the text.
    title = title.upper()
    f, size = fit(title, BRICOLAGE, 700, 32, -0.01, 660, 22)
    block_w = measure(title, f, -0.01 * size) / S + 40
    d.rectangle([576 * S, 464 * S, (576 + 348) * S, (464 + 60) * S], fill=YELLOW)
    d.rectangle([576 * S, 464 * S, (576 + block_w) * S, (464 + 60) * S], fill=PINK)
    tracked(d, 596, band_baseline(title, f, 464, 60), title, f, -0.01 * size, COCONUT)

    # --- builder number, bottom of the green identity panel ---
    f = font(JBMONO, 22, 700)
    tracked(d, 44, baseline_of(824, 22), f"BUILDER {number:03d}", f, 4.4, YELLOW)
    tracked(d, 388, baseline_of(824, 22), "/ 247", f, 4.4, COCONUT_70_ON_GREEN)

    # --- the three data columns under the ticker ---
    label_f = font(JBMONO, 14, 700)
    columns = [
        (576, "TEAM", team, 145),
        (730, "TRACK", TRACK, 180),
        (923, "CHECK-IN", check_in, 340),
    ]
    for x, label, value, avail in columns:
        tracked(d, x, baseline_of(746, 14), label, label_f, 2.8, INK)
        vf, vsize = fit(value, BRICOLAGE, 600, 30, -0.02, avail, 18)
        value = ellipsize(value, vf, -0.02, vsize, avail)
        # baseline stays at the 30px position so all three columns sit on one line after shrinking
        tracked(d, x, baseline_of(772, 30), value, vf, -0.02 * vsize, GREEN)

    # --- beach tile bar, footer, hashtag: all centred in their band, not on the spec's baseline ---
    tile_f = font(JBMONO, 15, 700)
    tracked(d, 1449, band_baseline("SUSEGAD MODE", tile_f, 489, 36), "SUSEGAD MODE", tile_f, 3,
            COCONUT, "center")
    foot_f = font(JBMONO, 19, 700)
    tracked(d, 597, band_baseline("SUSEGAD · SHIP ANYWAY", foot_f, 885, 57), "SUSEGAD · SHIP ANYWAY",
            foot_f, 3.8, INK)
    # spec says this dot is baked into the static layer; it isn't (no pink pixels in the footer band)
    d.ellipse([(1359 - 6) * S, (914 - 6) * S, (1359 + 6) * S, (914 + 6) * S], fill=PINK)
    tracked(d, 1543, band_baseline(HASHTAG, foot_f, 885, 57), HASHTAG, foot_f, 2.66, INK, "right")

    return card.resize((W, H), Image.LANCZOS)


def now_check_in():
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%-d %b · %H:%M")


def make_card(photo, name, stack, team, title=None):
    title = title or pick_title()
    card = render(photo, name, stack, team, title,
                  number=random.randint(1, 247), check_in=now_check_in())
    return card, title
