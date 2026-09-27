"""CLI: python scripts/preview_masks.py path/to/clip.mp4"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brickswap.config import Settings
from brickswap.pipeline import preview_masks


def main():
    if len(sys.argv) < 2:
        print("usage: preview_masks.py CLIP.mp4")
        sys.exit(2)
    clip = Path(sys.argv[1])
    sheet, movie, root, summary = preview_masks(clip, Settings.load(), lambda a, b, m: print(m))
    print(summary)
    print("sheet:", sheet)
    print("movie:", movie)
    print("job:", root)


if __name__ == "__main__":
    main()
