from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

CLASS_ALIASES = {
    "person": "person",
    "people": "person",
    "zombie": "person",
    "zombies": "person",
    "dog": "dog",
    "cat": "cat",
    "horse": "horse",
    "bird": "bird",
    "sheep": "sheep",
    "cow": "cow",
    "bear": "bear",
}


def parse_classes(text: str) -> list[str]:
    out = []
    for raw in text.split(","):
        key = raw.strip().lower()
        if not key:
            continue
        out.append(CLASS_ALIASES.get(key, key))
    return list(dict.fromkeys(out)) or ["person"]


_model = None


def load_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        _model = YOLO("yolo11n-seg.pt")
    return _model


def segment_frame(image_bgr: np.ndarray, classes: list[str], conf: float = 0.25) -> tuple[np.ndarray, list[dict]]:
    model = load_model()
    h, w = image_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    hits: list[dict] = []
    names = model.names
    want = set(classes)
    result = model.predict(image_bgr, verbose=False, conf=conf)[0]
    if result.masks is None or result.boxes is None:
        return mask, hits
    for i, box in enumerate(result.boxes):
        cls_id = int(box.cls.item())
        name = names.get(cls_id, str(cls_id))
        if name not in want:
            continue
        m = result.masks.data[i].cpu().numpy()
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
        binary = (m > 0.5).astype(np.uint8)
        if binary.sum() < 20:
            continue
        mask = np.maximum(mask, binary)
        ys, xs = np.where(binary > 0)
        hits.append({
            "class": name,
            "conf": float(box.conf.item()),
            "area": float(binary.mean()),
            "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
        })
    return mask, hits


def pad_mask(mask: np.ndarray, pad_frac: float) -> np.ndarray:
    if pad_frac <= 0:
        return mask
    h, w = mask.shape[:2]
    k = max(3, int(round(h * pad_frac)))
    if k % 2 == 0:
        k += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    return cv2.dilate(mask, kernel)


def feather_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    if radius <= 0:
        return (mask > 0).astype(np.float32)
    k = radius * 2 + 1
    soft = cv2.GaussianBlur(mask.astype(np.float32), (k, k), 0)
    return np.clip(soft, 0, 1)


def protect_bottom(mask: np.ndarray, frac: float) -> np.ndarray:
    if frac <= 0:
        return mask
    h = mask.shape[0]
    cut = int(h * (1.0 - frac))
    out = mask.copy()
    out[cut:] = 0
    return out


def temporal_smooth(masks: list[np.ndarray], passes: int = 1) -> list[np.ndarray]:
    if len(masks) < 3:
        return masks
    out = [m.copy() for m in masks]
    for _ in range(passes):
        nxt = [out[0]]
        for i in range(1, len(out) - 1):
            nxt.append(np.maximum(out[i], np.minimum(out[i - 1], out[i + 1])))
        nxt.append(out[-1])
        out = nxt
    return out


def overlay(frame: np.ndarray, mask: np.ndarray, color=(0, 0, 255), alpha=0.45) -> np.ndarray:
    vis = frame.copy()
    tint = np.zeros_like(frame)
    tint[:, :] = color
    m = (mask > 0).astype(np.float32)[..., None]
    vis = (vis * (1 - m * alpha) + tint * (m * alpha)).astype(np.uint8)
    contours, _ = cv2.findContours((mask > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(vis, contours, -1, color, 2)
    return vis


def process_frames(
    frames: list[Path],
    mask_dir: Path,
    classes: list[str],
    pad_frac: float,
    protect: float,
    progress=None,
) -> tuple[list[Path], list[dict]]:
    mask_dir.mkdir(parents=True, exist_ok=True)
    raw = []
    stats = []
    for i, fp in enumerate(frames):
        img = cv2.imread(str(fp))
        if img is None:
            raise RuntimeError(f"Unreadable frame {fp}")
        mask, hits = segment_frame(img, classes)
        mask = pad_mask(mask, pad_frac)
        mask = protect_bottom(mask, protect)
        raw.append(mask)
        area = float(mask.mean())
        stats.append({"frame": i, "area": area, "hits": hits, "closeup": area >= 0.30})
        if progress:
            progress(i + 1, len(frames), f"mask {i + 1}/{len(frames)}")
    raw = temporal_smooth(raw)
    paths = []
    for i, mask in enumerate(raw):
        dest = mask_dir / f"m_{i:06d}.png"
        cv2.imwrite(str(dest), mask * 255)
        paths.append(dest)
    return paths, stats
