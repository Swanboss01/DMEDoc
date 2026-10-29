"""Generates assets/dmedoc.ico and assets/dmedoc.png (needs Pillow).

Design: an ECU chip with pins and a heartbeat line (the "doctor" part).
Run from the repo root: python tools/make_icon.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

S = 1024  # drawing size; downscaled for each icon size
BG = (20, 33, 46)
CHIP = (38, 58, 78)
EDGE = (232, 236, 240)
PIN = (200, 205, 210)
PULSE = (46, 204, 113)


def draw() -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    d.rounded_rectangle((0, 0, S - 1, S - 1), radius=210, fill=BG)

    # chip body
    x0, y0, x1, y1 = 250, 250, 774, 774
    # pins (4 per side)
    pin_w, pin_len = 46, 110
    for i in range(4):
        c = x0 + 70 + i * ((x1 - x0 - 140) // 3)
        d.rounded_rectangle((c - pin_w // 2, y0 - pin_len, c + pin_w // 2, y0 + 20), radius=14, fill=PIN)
        d.rounded_rectangle((c - pin_w // 2, y1 - 20, c + pin_w // 2, y1 + pin_len), radius=14, fill=PIN)
        d.rounded_rectangle((x0 - pin_len, c - pin_w // 2, x0 + 20, c + pin_w // 2), radius=14, fill=PIN)
        d.rounded_rectangle((x1 - 20, c - pin_w // 2, x1 + pin_len, c + pin_w // 2), radius=14, fill=PIN)
    d.rounded_rectangle((x0, y0, x1, y1), radius=70, fill=CHIP, outline=EDGE, width=22)

    # heartbeat line
    cy = (y0 + y1) // 2
    pts = [
        (x0 + 60, cy),
        (x0 + 170, cy),
        (x0 + 225, cy - 150),
        (x0 + 300, cy + 140),
        (x0 + 360, cy - 60),
        (x0 + 400, cy),
        (x1 - 60, cy),
    ]
    d.line(pts, fill=PULSE, width=36, joint="curve")
    for p in (pts[0], pts[-1]):
        d.ellipse((p[0] - 18, p[1] - 18, p[0] + 18, p[1] + 18), fill=PULSE)
    return img


def main() -> None:
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    os.makedirs(out, exist_ok=True)
    img = draw()
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(out, "dmedoc.png"))
    img.save(
        os.path.join(out, "dmedoc.ico"),
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("wrote", out)


if __name__ == "__main__":
    main()
