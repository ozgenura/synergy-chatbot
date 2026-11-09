"""Maskot karelerini tek görselde gösterir: python scripts/preview_mascot.py"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

from mascot_art import HEIGHT, MOODS, PALETTE, WIDTH, runs, sprite  # noqa: E402

SCALE = 6
CELL_W, CELL_H = (WIDTH + 4) * SCALE, (HEIGHT + 4) * SCALE + 18


def main() -> None:
    sheet = Image.new("RGB", (CELL_W * len(MOODS), CELL_H * 2), "#e9edf3")
    draw = ImageDraw.Draw(sheet)
    for column, mood in enumerate(MOODS):
        for row in range(2):
            ox, oy = column * CELL_W + 2 * SCALE, row * CELL_H + 18
            draw.text((column * CELL_W + 6, row * CELL_H + 3), f"{mood} {row}", fill="#000000")
            for x, y, width, color in runs(sprite(mood, row)):
                draw.rectangle((ox + x * SCALE, oy + y * SCALE, ox + (x + width) * SCALE - 1, oy + (y + 1) * SCALE - 1), fill=PALETTE[color])
    out = ROOT / "results" / "mascot_sheet.png"
    out.parent.mkdir(exist_ok=True)
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
