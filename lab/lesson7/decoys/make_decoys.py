#!/usr/bin/env python3
"""make_decoys.py -- draw generic decoy objects for any scenario.

Decoys are things a search drone will find that are NOT the missing person's.
These are clearly different kinds of object (not near-misses), drawn with
../icon_kit.py at the people icons' scale, so place them at the same width_m
as the person (8 m) and they are life-size relative to them:

    mans-brown-oxford-shoe.png   ~30 cm adult leather shoe
    doll-pink-dress.png          ~40 cm plastic doll
    soccer-ball.png              ~22 cm football

    python make_decoys.py
"""
import math
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from icon_kit import LINE_W, N, OUTLINE, PX_PER_M, SS, blob, canvas, finish, rotated_ellipse, s, shade, texture  # noqa: E402


def out(name):
    return os.path.join(HERE, name)


def shoe():
    """Man's brown leather oxford, ~30 cm, lying at an angle, laced."""
    length, half_w = 0.30 * PX_PER_M * SS, 0.055 * PX_PER_M * SS
    w, h = int(length + 8 * LINE_W), int(2 * half_w + 8 * LINE_W)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    x0, cy = 4 * LINE_W, h / 2

    def outline_pts(grow=0.0):
        pts_top, pts_bot = [], []
        for i in range(61):
            t = i / 60
            if t < 0.35:
                hw = 0.70 + 0.20 * math.sin(t / 0.35 * math.pi / 2) * 0.5 + 0.15 * (1 - t / 0.35) ** 2
            elif t < 0.78:
                hw = 0.82 + 0.18 * (t - 0.35) / 0.43
            else:
                hw = math.sqrt(max(0.0, 1 - ((t - 0.78) / 0.22) ** 2))
            if t < 0.10:                                   # rounded heel
                hw *= math.sqrt(max(0.0, 1 - ((0.10 - t) / 0.10) ** 2))
            hw = hw * half_w + grow
            x = x0 + t * length + (grow if t > 0.5 else -grow)
            pts_top.append((x, cy - hw))
            pts_bot.append((x, cy + hw * (0.92 if 0.3 < t < 0.7 else 1.0)))  # arch side slightly in
        return pts_top + pts_bot[::-1]

    d = ImageDraw.Draw(layer)
    sole, leather, light, inside, lace = ((58, 34, 20, 255), (122, 70, 36, 255), (160, 102, 58, 255),
                                         (196, 160, 112, 255), (214, 190, 140, 255))
    flat = lambda pts: [c for p in pts for c in p]  # noqa: E731
    blob(layer, "polygon", flat(outline_pts(6 * SS)), sole)
    d.polygon(flat(outline_pts(0)), fill=leather)
    # toe cap seam and a broguing-free plain vamp
    tx = x0 + 0.80 * length
    d.arc((tx - 0.12 * length, cy - half_w * 0.95, tx + 0.04 * length, cy + half_w * 0.95), 290, 70,
          fill=OUTLINE, width=3 * SS)
    # heel opening, showing the tan insole
    ox0, ox1 = x0 + 0.07 * length, x0 + 0.37 * length
    blob(layer, "ellipse", (ox0, cy - half_w * 0.48, ox1, cy + half_w * 0.48), (40, 26, 16, 255), width=4 * SS)
    d.ellipse((ox0 + 10 * SS, cy - half_w * 0.36, ox1 - 6 * SS, cy + half_w * 0.36), fill=inside)
    # lacing: eyelet facings, eyelets, criss-cross laces, a bow
    fx0, fx1 = x0 + 0.40 * length, x0 + 0.64 * length
    for side in (-1, 1):
        blob(layer, "polygon", [fx0, cy + side * 4 * SS, fx1, cy + side * 3 * SS,
                                fx1 - 6 * SS, cy + side * half_w * 0.48, fx0, cy + side * half_w * 0.58], light,
             width=3 * SS)
    xs = [fx0 + (fx1 - fx0) * k / 4 + 8 * SS for k in range(4)]
    for i, x in enumerate(xs):
        for side in (-1, 1):
            d.ellipse((x - 5 * SS, cy + side * half_w * 0.36 - 5 * SS, x + 5 * SS, cy + side * half_w * 0.36 + 5 * SS),
                      fill=OUTLINE)
        if i:
            d.line((xs[i - 1], cy - half_w * 0.36, x, cy + half_w * 0.36), fill=lace, width=5 * SS)
            d.line((xs[i - 1], cy + half_w * 0.36, x, cy - half_w * 0.36), fill=lace, width=5 * SS)
    bx = xs[0] - 2 * SS
    for dy in (-1, 1):
        blob(layer, "ellipse", (bx - 22 * SS, cy + dy * 18 * SS - 8 * SS, bx + 2 * SS, cy + dy * 18 * SS + 8 * SS),
             lace, width=3 * SS)
    d.line((bx, cy, bx - 30 * SS, cy - 34 * SS), fill=lace, width=4 * SS)
    d.line((bx, cy, bx - 24 * SS, cy + 40 * SS), fill=lace, width=4 * SS)
    # leather highlight
    d.line((x0 + 0.70 * length, cy - half_w * 0.55, x0 + 0.92 * length, cy - half_w * 0.35),
           fill=(190, 136, 86, 255), width=6 * SS)
    layer = layer.rotate(28, resample=Image.BICUBIC, expand=True)
    img = canvas()
    img.alpha_composite(layer, (int(N / 2 - layer.width / 2), int(N / 2 - layer.height / 2)))
    texture(img, 10, 0.04, seed=3, mark=2)
    shade(img, strength=45)
    finish(img, out("mans-brown-oxford-shoe.png"))


def doll():
    """~40 cm plastic doll lying face up: blonde hair, pink dress, white shoes."""
    img = canvas()
    skin, hair, hair_dark = (246, 206, 176, 255), (240, 206, 92, 255), (204, 160, 52, 255)
    pink, pink_dark, white = (236, 110, 160, 255), (196, 70, 122, 255), (250, 248, 240, 255)
    # hair fanned out behind the head
    blob(img, "ellipse", s(424, 262, 600, 432), hair)
    for x, a in ((420, 25), (604, -25)):
        rotated_ellipse(img, *s(x, 410), *s(46, 120), a, hair)
    # legs and shoes
    for x in (480, 544):
        blob(img, "polygon", s(x - 18, 600, x + 18, 600, x + 16, 744, x - 16, 744), skin)
        blob(img, "ellipse", s(x - 22, 732, x + 22, 772), white)
        ImageDraw.Draw(img).line(s(x - 18, 744, x + 18, 744), fill=OUTLINE, width=3 * SS)
    # arms, out to the sides
    rotated_ellipse(img, *s(420, 488), *s(34, 140), -55, skin)
    rotated_ellipse(img, *s(604, 488), *s(34, 140), 55, skin)
    # dress with white collar and lace hem
    blob(img, "polygon", s(472, 420, 552, 420, 600, 612, 424, 612), pink)
    d = ImageDraw.Draw(img)
    for x in range(430, 596, 16):
        d.ellipse(s(x, 600, x + 16, 618), fill=white, outline=OUTLINE, width=2 * SS)
    d.line(s(512, 440, 512, 600), fill=pink_dark, width=4 * SS)
    for y in (470, 510, 550):
        d.ellipse(s(505, y - 7, 519, y + 7), fill=white, outline=OUTLINE, width=2 * SS)
    blob(img, "polygon", s(472, 420, 512, 440, 552, 420, 540, 452, 512, 462, 484, 452), white, width=4 * SS)
    # head and face
    blob(img, "ellipse", s(458, 300, 566, 416), skin)
    d.chord(s(456, 296, 568, 360), 180, 360, fill=hair)                              # fringe
    for ex in (490, 534):
        d.ellipse(s(ex - 11, 352, ex + 11, 374), fill=white, outline=OUTLINE, width=3 * SS)
        d.ellipse(s(ex - 7, 356, ex + 7, 372), fill=(60, 120, 210, 255))
        d.ellipse(s(ex - 3, 360, ex + 3, 368), fill=OUTLINE)
        d.arc(s(ex - 13, 336, ex + 13, 352), 200, 340, fill=hair_dark, width=3 * SS)  # brows
    d.ellipse(s(474, 378, 490, 388), fill=(244, 160, 160, 255))                     # cheeks
    d.ellipse(s(534, 378, 550, 388), fill=(244, 160, 160, 255))
    d.ellipse(s(504, 390, 520, 400), fill=(214, 70, 100, 255))                      # mouth
    shade(img, strength=40)
    finish(img, out("doll-pink-dress.png"))


def ball():
    """Classic black-and-white football, ~22 cm."""
    r = 0.11 * PX_PER_M * SS
    cx = cy = N / 2
    img = canvas()
    blob(img, "ellipse", (cx - r, cy - r, cx + r, cy + r), (246, 246, 242, 255))
    panels = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(panels)

    def pentagon(px, py, size, rot, squash=1.0, toward=0.0):
        pts = []
        for k in range(5):
            a = rot + k * 2 * math.pi / 5
            dx, dy = size * math.cos(a), size * math.sin(a)
            # foreshorten radially for panels near the rim
            along = dx * math.cos(toward) + dy * math.sin(toward)
            perp = -dx * math.sin(toward) + dy * math.cos(toward)
            along *= squash
            pts += [px + along * math.cos(toward) - perp * math.sin(toward),
                    py + along * math.sin(toward) + perp * math.cos(toward)]
        return pts

    center = pentagon(cx, cy, r * 0.30, -math.pi / 2)
    d.polygon(center, fill=(28, 28, 30, 255))
    for k in range(5):
        a = -math.pi / 2 + math.pi / 5 + k * 2 * math.pi / 5
        px, py = cx + r * 0.80 * math.cos(a), cy + r * 0.80 * math.sin(a)
        d.polygon(pentagon(px, py, r * 0.30, a + math.pi, squash=0.55, toward=a), fill=(28, 28, 30, 255))
        # seams from the centre panel's corners to the rim panels
        ca = -math.pi / 2 + k * 2 * math.pi / 5
        d.line((cx + r * 0.30 * math.cos(ca), cy + r * 0.30 * math.sin(ca),
                cx + r * 0.66 * math.cos(ca), cy + r * 0.66 * math.sin(ca)), fill=(120, 120, 120, 255), width=3 * SS)
    mask = Image.new("L", (N, N), 0)
    ImageDraw.Draw(mask).ellipse((cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2), fill=255)
    img.paste(panels, (0, 0), Image.composite(panels.getchannel("A"), mask, mask).point(lambda v: v))
    ImageDraw.Draw(img).ellipse((cx - r, cy - r, cx + r, cy + r), outline=OUTLINE, width=LINE_W)
    # sphere shading: darken toward bottom-right, highlight top-left
    shade_l = Image.new("L", (N, N), 0)
    sd = ImageDraw.Draw(shade_l)
    for i in range(30):
        f = i / 30
        sd.ellipse((cx - r * (1 - f) + r * 0.25 * f, cy - r * (1 - f) + r * 0.25 * f,
                    cx + r * (1 - f) + r * 0.25 * f, cy + r * (1 - f) + r * 0.25 * f), fill=int(70 * (1 - f)))
    shade_l = Image.composite(shade_l, Image.new("L", (N, N), 0), mask)
    img.paste(Image.new("RGBA", (N, N), (30, 30, 40, 255)), (0, 0), shade_l)
    ImageDraw.Draw(img).ellipse((cx - r * 0.55, cy - r * 0.62, cx - r * 0.25, cy - r * 0.40),
                                fill=(255, 255, 255, 200))
    finish(img, out("soccer-ball.png"))


if __name__ == "__main__":
    shoe()
    doll()
    ball()
