#!/usr/bin/env python3
"""make_icons.py -- draw this scenario's clue icons (transparent PNGs).

Drawn with ../../icon_kit.py at the people icons' scale: place each at the
same width_m as the girl (8 m) and it is the right size relative to her.

    python make_icons.py            # writes images/teddy-bear-red-bow.png, images/lime-cardigan.png
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))

from icon_kit import LINE_W, OUTLINE, SS, blob, canvas, finish, rotated_ellipse, s, shade, texture  # noqa: E402,F401
from PIL import ImageDraw  # noqa: E402

def teddy():
    """~30 cm brown teddy bear lying face-up, red ribbon bow at the neck."""
    img = canvas()
    fur, light, pad = (139, 94, 52, 255), (196, 150, 98, 255), (214, 178, 128, 255)
    rotated_ellipse(img, *s(432, 640), *s(78, 104), 18, fur, inner=(s(48)[0], s(52)[0], pad))   # legs
    rotated_ellipse(img, *s(592, 640), *s(78, 104), -18, fur, inner=(s(48)[0], s(52)[0], pad))
    rotated_ellipse(img, *s(398, 520), *s(64, 116), -38, fur)                                   # arms
    rotated_ellipse(img, *s(626, 520), *s(64, 116), 38, fur)
    blob(img, "ellipse", s(424, 448, 600, 650), fur)                                            # body
    ImageDraw.Draw(img).ellipse(s(462, 500, 562, 620), fill=light)                              # belly
    for ex in (452, 572):                                                                       # ears
        blob(img, "ellipse", s(ex - 34, 318, ex + 34, 386), fur)
        ImageDraw.Draw(img).ellipse(s(ex - 18, 334, ex + 18, 370), fill=pad)
    blob(img, "ellipse", s(428, 336, 596, 492), fur)                                            # head
    d = ImageDraw.Draw(img)
    d.ellipse(s(474, 418, 550, 474), fill=light)                                                # muzzle
    d.ellipse(s(498, 424, 526, 442), fill=OUTLINE)                                              # nose
    d.line(s(512, 442, 512, 456), fill=OUTLINE, width=4 * SS)
    d.arc(s(494, 444, 530, 466), 20, 160, fill=OUTLINE, width=4 * SS)
    for ex in (482, 542):                                                                       # eyes
        d.ellipse(s(ex - 10, 394, ex + 10, 414), fill=OUTLINE)
        d.ellipse(s(ex - 5, 397, ex, 402), fill=(255, 255, 255, 255))
    texture(img, 26, 0.08, seed=1, mark=3)
    red, dark_red = (206, 32, 38, 255), (150, 18, 26, 255)                                      # bow
    blob(img, "polygon", s(512, 498, 452, 470, 446, 530), red)
    blob(img, "polygon", s(512, 498, 572, 470, 578, 530), red)
    blob(img, "polygon", s(500, 506, 482, 556, 500, 552), dark_red)
    blob(img, "polygon", s(524, 506, 542, 556, 524, 552), dark_red)
    blob(img, "ellipse", s(498, 484, 526, 512), dark_red)
    shade(img, strength=55)
    finish(img, os.path.join(HERE, "images", "teddy-bear-red-bow.png"))


def cardigan():
    """Child's lime-green knit cardigan, dropped flat and a bit crumpled, buttons undone at top."""
    img = canvas()
    lime, lime_dark, inside = (150, 206, 46, 255), (110, 160, 30, 255), (96, 140, 32, 255)
    rib = (128, 182, 38, 255)
    # back of the garment, seen through the open neck
    blob(img, "polygon", s(452, 300, 572, 300, 540, 490, 484, 490), inside)
    # left sleeve (spread out) and right sleeve (bent back toward the hem)
    blob(img, "polygon", s(360, 318, 268, 372, 176, 500, 230, 548, 312, 452, 356, 470), lime)
    blob(img, "polygon", s(150, 490, 208, 548, 236, 522, 180, 462), rib)
    blob(img, "polygon", s(664, 318, 752, 392, 792, 540, 742, 566, 700, 470, 668, 470), lime)
    blob(img, "polygon", s(736, 556, 800, 534, 812, 576, 750, 598), rib)
    # left front panel (buttons) and right front panel (buttonholes), overlapping at centre
    blob(img, "polygon", s(452, 300, 360, 318, 350, 470, 342, 712, 518, 724, 516, 470), lime)
    blob(img, "polygon", s(572, 300, 664, 318, 676, 470, 690, 704, 506, 724, 508, 470), lime)
    # ribbed hem and button band
    blob(img, "polygon", s(342, 690, 518, 702, 518, 748, 340, 736), rib)
    blob(img, "polygon", s(506, 702, 690, 682, 694, 728, 506, 748), rib)
    d = ImageDraw.Draw(img)
    for x in range(352, 690, 14):                                                               # rib lines
        if x < 512:   # left hem band: top 690->702, bottom 736->748 across x 342..518
            f = (x - 342) / 176
            top, bottom = 690 + 12 * f, 736 + 12 * f
        else:         # right hem band: top 702->682, bottom 748->728 across x 506..690
            f = (x - 506) / 184
            top, bottom = 702 - 20 * f, 748 - 20 * f
        d.line(s(x, top + 6, x, bottom - 6), fill=lime_dark, width=2 * SS)
    d.line(s(508, 470, 452, 304), fill=OUTLINE, width=4 * SS)                                   # V-neck edges
    d.line(s(508, 470, 572, 304), fill=OUTLINE, width=4 * SS)
    d.line(s(512, 470, 512, 700), fill=OUTLINE, width=4 * SS)                                   # front opening
    for y in range(498, 690, 44):                                                               # buttons
        d.ellipse(s(482, y - 11, 504, y + 11), fill=OUTLINE)
        d.ellipse(s(485, y - 8, 501, y + 8), fill=(244, 236, 214, 255))
        d.point(s(491, y - 2) + s(497, y + 2), fill=OUTLINE)
    for crease in ((390, 380, 430, 560), (610, 400, 590, 600), (250, 430, 300, 470), (720, 430, 735, 520)):
        d.line(s(*crease), fill=lime_dark, width=5 * SS)                                        # fold creases
    texture(img, 18, 0.10, seed=2, mark=2)
    shade(img, strength=45)
    finish(img, os.path.join(HERE, "images", "lime-cardigan.png"))


if __name__ == "__main__":
    teddy()
    cardigan()
