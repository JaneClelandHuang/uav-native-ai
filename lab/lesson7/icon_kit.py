"""icon_kit.py -- shared drawing helpers for clue icons (transparent PNGs).

Scale convention: a 1024x1024 canvas at the same scale as new-gui's
people/girl-pinafores.png (~1150 px per real metre). An icon placed at the
same width_m as a person (8 m by default) is the right size next to them.
Draw at supersampled size with s(...) coordinates in 1024-space, then finish().
"""
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

PX_PER_M = 1150             # canvas pixels per real metre

SS = 2                      # supersampling factor, for smooth edges
N = 1024 * SS
OUTLINE = (24, 18, 14, 255)
LINE_W = 7 * SS


def s(*v):
    return [x * SS for x in v]


def canvas():
    return Image.new("RGBA", (N, N), (0, 0, 0, 0))


def blob(img, shape, box_or_pts, fill, outline=True, width=LINE_W):
    """Draw a filled shape with a thick dark outline (outline drawn first, fill inset)."""
    d = ImageDraw.Draw(img)
    if shape == "ellipse":
        x0, y0, x1, y1 = box_or_pts
        if outline:
            d.ellipse((x0 - width, y0 - width, x1 + width, y1 + width), fill=OUTLINE)
        d.ellipse((x0, y0, x1, y1), fill=fill)
    else:
        if outline:
            d.polygon(box_or_pts, fill=OUTLINE)
            d.line(box_or_pts + box_or_pts[:2], fill=OUTLINE, width=width * 2, joint="curve")
        d.polygon(box_or_pts, fill=fill)


def rotated_ellipse(img, cx, cy, w, h, angle, fill, inner=None):
    layer = Image.new("RGBA", (int(w + 4 * LINE_W), int(h + 4 * LINE_W)), (0, 0, 0, 0))
    ox, oy = 2 * LINE_W, 2 * LINE_W
    blob(layer, "ellipse", (ox, oy, ox + w, oy + h), fill)
    if inner:
        iw, ih, icol = inner
        d = ImageDraw.Draw(layer)
        d.ellipse((ox + (w - iw) / 2, oy + h - ih - 8 * SS, ox + (w + iw) / 2, oy + h - 8 * SS), fill=icol)
    layer = layer.rotate(angle, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(layer, (int(cx - layer.width / 2), int(cy - layer.height / 2)))


def texture(img, color_jitter, density, seed, mark=1):
    """Speckle the opaque, non-outline pixels: fur or knit grain."""
    rng = random.Random(seed)
    px = img.load()
    for _ in range(int(N * N * density)):
        x, y = rng.randrange(N), rng.randrange(N)
        r, g, b, a = px[x, y]
        if a < 250 or (r + g + b) < 120:
            continue
        j = rng.randint(-color_jitter, color_jitter)
        for dx in range(mark):
            for dy in range(mark):
                if x + dx < N and y + dy < N and px[x + dx, y + dy][3] == 255:
                    px[x + dx, y + dy] = (max(0, min(255, r + j)), max(0, min(255, g + j)),
                                          max(0, min(255, b + j // 2)), 255)


def shade(img, light=(-0.6, -0.8), strength=60):
    """Darken the side away from the light (top-left), like the people icons."""
    alpha = img.getchannel("A")
    grad = Image.new("L", (N, N))
    gp = grad.load()
    for y in range(0, N, 4):
        for x in range(0, N, 4):
            t = ((x / N - 0.5) * -light[0] + (y / N - 0.5) * -light[1])  # -0.7 .. 0.7
            v = int(max(0, min(255, (t + 0.3) * strength * 2)))
            for dy in range(4):
                for dx in range(4):
                    gp[x + dx, y + dy] = v
    dark = Image.new("RGBA", (N, N), (20, 12, 0, 255))
    mask = ImageChops.multiply(grad, alpha)
    img.paste(dark, (0, 0), mask.point(lambda v: v * strength // 255))


def finish(img, path):
    """Soft drop shadow (partial alpha, like the people icons), downsample, save."""
    alpha = img.getchannel("A")
    shadow = Image.new("RGBA", (N, N), (30, 22, 10, 0))
    shadow.putalpha(alpha.filter(ImageFilter.GaussianBlur(18 * SS)).point(lambda v: v * 120 // 255))
    out = canvas()
    out.alpha_composite(shadow, (6 * SS, 10 * SS))
    out.alpha_composite(img)
    out = out.resize((1024, 1024), Image.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.save(path)
    print(f"wrote {path}  bbox {out.getbbox()}")
