"""Render docs/assets/readme/sorting-floor.gif — the README's pixel-art mailroom loop.

Letters drop from a chute, ride the belt under the SORTER (classify) and the
JUDGE stamp, then hop into one of the five live document-class bins while a
hash-chain receipt grows along the floor. Everything is periodic, so the GIF
loops seamlessly.

    uv run --frozen python docs/assets/readme/make_sorting_gif.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).with_name("sorting-floor.gif")
LW, LH, SCALE = 240, 92, 4  # low-res canvas, upscaled with nearest-neighbour
PERIOD, SPAWN = 200, 20  # frames per loop, frames between letters
BELT_Y, BELT_X0, BELT_X1, SPEED = 58, 14, 172, 1.25
SORTER_X, JUDGE_X = 78, 128

BG, FLOOR, BELT, ROLLER = (11, 18, 32), (20, 28, 46), (51, 65, 85), (100, 116, 139)
PAPER, INK = (229, 231, 235), (100, 116, 139)
CLASSES = [  # (bin label, colour) — the five live classes in docs/v7-taxonomy.md
    ("CNTR", (56, 189, 248)),
    ("M&A", (192, 132, 252)),
    ("CORP", (250, 204, 21)),
    ("CORR", (34, 197, 94)),
    ("CLAIM", (244, 114, 182)),
]
SEQ = [0, 3, 4, 1, 2, 3, 0, 4, 2, 1]  # PERIOD // SPAWN letters per loop
BIN_W, BIN_X0, BIN_Y = 12, 178, 52


def font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def letter_pos(age: int) -> tuple[float, float, str] | None:
    """Return (x, y, phase) of a letter `age` frames after it spawned."""
    fall = 10
    if age < fall:
        return BELT_X0, 14 + (BELT_Y - 6 - 14) * (age / fall) ** 2, "fall"
    x = BELT_X0 + (age - fall) * SPEED
    if x <= BELT_X1:
        return x, BELT_Y - 6, "belt"
    return None


def hop(cls: int, t: float) -> tuple[float, float]:
    """Parabolic hop from the belt end into a bin, t in [0, 1]."""
    tx = BIN_X0 + cls * BIN_W + 2
    x = BELT_X1 + (tx - BELT_X1) * t
    y = (BELT_Y - 6) + (BIN_Y + 18 - (BELT_Y - 6)) * t - 40 * t * (1 - t)
    return x, y


def draw_letter(d: ImageDraw.ImageDraw, x: float, y: float, cls: int | None, stamped: bool) -> None:
    x, y = int(x), int(y)
    edge = CLASSES[cls][1] if cls is not None else INK
    d.rectangle([x, y, x + 8, y + 5], fill=PAPER, outline=edge)
    d.line([x, y, x + 4, y + 3], fill=edge)
    d.line([x + 4, y + 3, x + 8, y], fill=edge)
    if stamped:
        d.point([(x + 6, y + 4), (x + 7, y + 3)], fill=(22, 163, 74))


def frame(f: int, big: ImageFont.ImageFont, small: ImageFont.ImageFont) -> Image.Image:
    im = Image.new("RGB", (LW, LH), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 76, LW, LH], fill=FLOOR)

    # chute
    d.rectangle([BELT_X0 - 4, 4, BELT_X0 + 12, 12], fill=(30, 41, 59), outline=ROLLER)
    # belt + rollers (rollers "spin" by alternating a highlight pixel)
    d.rectangle([BELT_X0 - 4, BELT_Y, BELT_X1 + 2, BELT_Y + 3], fill=BELT)
    for rx in range(BELT_X0, BELT_X1 + 1, 10):
        d.ellipse([rx - 2, BELT_Y + 4, rx + 2, BELT_Y + 8], fill=(30, 41, 59), outline=ROLLER)
        spin = (f // 2 + rx) % 4
        d.point((rx - 1 + spin % 3, BELT_Y + 6), fill=(203, 213, 225))
    for sx in range(BELT_X0 - 4 + (f % 6), BELT_X1, 6):
        d.point((sx, BELT_Y + 1), fill=ROLLER)

    letters = []
    for k in range(f // SPAWN - 12, f // SPAWN + 1):
        spawn = k * SPAWN
        age = f - spawn
        if age < 0:
            continue
        letters.append((age, SEQ[k % len(SEQ)]))

    scanning, stamping = None, False
    landed = [0] * len(CLASSES)
    for age, cls in letters:
        pos = letter_pos(age)
        if pos is None:
            belt_age = int(10 + (BELT_X1 - BELT_X0) / SPEED)
            t = (age - belt_age) / 12
            if t > 1:
                if t < 2.2:
                    landed[cls] = max(landed[cls], int(8 * (2.2 - t)))
                continue
            x, y = hop(cls, t)
            draw_letter(d, x, y, cls, True)
            continue
        x, y, _ = pos
        known = cls if x > SORTER_X + 2 else None
        if SORTER_X - 6 <= x <= SORTER_X + 2:
            scanning = cls
        if JUDGE_X - 5 <= x <= JUDGE_X + 1:
            stamping = True
        draw_letter(d, x, y, known, x > JUDGE_X + 1)

    # SORTER robot (classify) with scan beam
    d.rectangle([SORTER_X - 4, 32, SORTER_X + 12, 46], fill=(51, 65, 85), outline=ROLLER)
    d.rectangle([SORTER_X + 1, 28, SORTER_X + 7, 32], fill=(30, 41, 59))
    eye = CLASSES[scanning][1] if scanning is not None else ((148, 163, 184) if f % 24 < 21 else (51, 65, 85))
    d.rectangle([SORTER_X, 36, SORTER_X + 8, 40], fill=eye)
    if scanning is not None:
        beam = CLASSES[scanning][1]
        for by in range(47, BELT_Y - 6, 2):
            d.line([SORTER_X + 1, by, SORTER_X + 7, by], fill=tuple(int(c * 0.55) for c in beam))

    # JUDGE stamp piston
    drop = 7 if stamping else 0
    d.rectangle([JUDGE_X - 1, 26, JUDGE_X + 9, 32], fill=(51, 65, 85), outline=ROLLER)
    d.rectangle([JUDGE_X + 3, 32, JUDGE_X + 5, 40 + drop], fill=ROLLER)
    d.rectangle([JUDGE_X, 40 + drop, JUDGE_X + 8, 43 + drop], fill=(22, 163, 74))

    # bins
    for i, (_, col) in enumerate(CLASSES):
        bx = BIN_X0 + i * BIN_W
        glow = landed[i]
        fill = tuple(int(c * (0.18 + 0.08 * glow)) for c in col)
        d.rectangle([bx, BIN_Y + 14, bx + BIN_W - 2, BIN_Y + 30], fill=fill, outline=col)

    # hash chain receipt: one block per archived letter, scrolling left forever
    shift = (f % SPAWN) * 10 / SPAWN
    for j in range(18):
        cx = int(166 - j * 10 - (10 - shift))
        if cx < 6:
            break
        col = CLASSES[SEQ[(f // SPAWN - j) % len(SEQ)]][1]
        d.rectangle([cx, 82, cx + 6, 87], fill=FLOOR, outline=col)
        d.line([cx + 7, 84, cx + 9, 84], fill=ROLLER)

    big_im = im.resize((LW * SCALE, LH * SCALE), Image.NEAREST)
    bd = ImageDraw.Draw(big_im)
    bd.text((36 * SCALE, 3 * SCALE), "THE MAILROOM · LIVE SORTING FLOOR", font=big, fill=(203, 213, 225))
    bd.text(((BELT_X0 + 4) * SCALE, 8 * SCALE), "INBOX", font=small, fill=(148, 163, 184), anchor="mm")
    bd.text(((SORTER_X - 6) * SCALE, 21 * SCALE), "SORTER", font=small, fill=(148, 163, 184))
    bd.text(((JUDGE_X - 2) * SCALE, 20 * SCALE), "JUDGE", font=small, fill=(148, 163, 184))
    bd.text((6 * SCALE, 77 * SCALE - 2), "hash-chained archive →", font=small, fill=(100, 116, 139))
    for i, (label, col) in enumerate(CLASSES):
        bx = (BIN_X0 + i * BIN_W + (BIN_W - 2) / 2) * SCALE
        bd.text((bx, (BIN_Y + 10) * SCALE), label, font=small, fill=col, anchor="ms")
    return big_im


def main() -> None:
    big, small = font(22), font(13)
    frames = [frame(PERIOD + f, big, small) for f in range(PERIOD)]  # steady state
    pal = [fr.convert("P", palette=Image.ADAPTIVE, colors=64) for fr in frames]
    pal[0].save(OUT, save_all=True, append_images=pal[1:], duration=45, loop=0, optimize=True, disposal=1)
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.0f} KiB, {len(frames)} frames)")


if __name__ == "__main__":
    main()
