from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .detect import feather_mask


def composite_back(
    generated: np.ndarray,
    original: np.ndarray,
    mask: np.ndarray,
    feather: int = 7,
) -> np.ndarray:
    """Keep original pixels outside the subject. Blend generated pixels inside."""
    if generated.shape[:2] != original.shape[:2]:
        generated = cv2.resize(generated, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_CUBIC)
    if mask.shape[:2] != original.shape[:2]:
        mask = cv2.resize(mask, (original.shape[1], original.shape[0]), interpolation=cv2.INTER_LINEAR)
    alpha = feather_mask(mask, feather)[..., None]
    out = original.astype(np.float32) * (1 - alpha) + generated.astype(np.float32) * alpha
    return np.clip(out, 0, 255).astype(np.uint8)


def composite_folder(
    gen_dir: Path,
    orig_frames: list[Path],
    mask_paths: list[Path],
    dest_dir: Path,
    feather: int = 7,
) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    gen_frames = sorted(gen_dir.glob("*.png")) + sorted(gen_dir.glob("*.jpg"))
    if not gen_frames:
        raise RuntimeError(f"No generated frames in {gen_dir}")
    n = min(len(gen_frames), len(orig_frames), len(mask_paths))
    out = []
    for i in range(n):
        g = cv2.imread(str(gen_frames[i]))
        o = cv2.imread(str(orig_frames[i]))
        m = cv2.imread(str(mask_paths[i]), cv2.IMREAD_GRAYSCALE)
        if g is None or o is None or m is None:
            continue
        blended = composite_back(g, o, m, feather)
        dest = dest_dir / f"c_{i:06d}.png"
        cv2.imwrite(str(dest), blended)
        out.append(dest)
    return out
