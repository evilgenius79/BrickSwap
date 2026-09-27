from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np


def ffmpeg_bin() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("ffmpeg not found on PATH") from exc


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-4000:] or proc.stdout[-4000:] or "ffmpeg failed")


def video_info(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    duration = frames / fps if fps else 0.0
    return {"fps": fps, "frames": frames, "width": w, "height": h, "duration": duration}


def even16(n: int) -> int:
    n = max(16, n)
    return n - (n % 16)


def fit_size(w: int, h: int, max_long: int) -> tuple[int, int]:
    scale = min(1.0, max_long / max(w, h))
    return even16(int(w * scale)), even16(int(h * scale))


def extract_frames(
    src: Path,
    dest: Path,
    fps: int,
    max_long: int,
    start_sec: float = 0.0,
    duration: float | None = None,
) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    info = video_info(src)
    tw, th = fit_size(info["width"], info["height"], max_long)
    vf = f"fps={fps},scale={tw}:{th}:flags=lanczos"
    out = dest / "f_%06d.png"
    cmd = [ffmpeg_bin(), "-y", "-ss", f"{start_sec:.3f}", "-i", str(src)]
    if duration is not None:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-vf", vf, "-start_number", "0", str(out)]
    run(cmd)
    frames = sorted(dest.glob("f_*.png"))
    if not frames:
        raise RuntimeError("No frames extracted")
    return frames


def detect_cuts(frames: list[Path], threshold: float = 0.32) -> list[int]:
    """Histogram scene-cut detector. Returns frame indices where a new shot starts."""
    cuts = [0]
    prev = None
    for i, p in enumerate(frames):
        img = cv2.imread(str(p))
        if img is None:
            continue
        hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        if prev is not None:
            diff = cv2.compareHist(prev, hist, cv2.HISTCMP_BHATTACHARYYA)
            if diff >= threshold and i - cuts[-1] >= 4:
                cuts.append(i)
        prev = hist
    return cuts


def write_video(frames: list[Path], dest: Path, fps: int) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not frames:
        raise RuntimeError("No frames to write")
    first = cv2.imread(str(frames[0]))
    h, w = first.shape[:2]
    tmp = dest.with_suffix(".raw.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(tmp), fourcc, fps, (w, h))
    for p in frames:
        im = cv2.imread(str(p))
        if im is None:
            continue
        if im.shape[1] != w or im.shape[0] != h:
            im = cv2.resize(im, (w, h))
        writer.write(im)
    writer.release()
    run([
        ffmpeg_bin(), "-y", "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        str(dest),
    ])
    tmp.unlink(missing_ok=True)
    return dest


def mux_audio(video: Path, source_clip: Path, dest: Path, start_sec: float = 0.0, duration: float | None = None) -> Path:
    cmd = [ffmpeg_bin(), "-y", "-i", str(video), "-ss", f"{start_sec:.3f}", "-i", str(source_clip)]
    if duration is not None:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += [
        "-map", "0:v:0", "-map", "1:a:0?",
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        str(dest),
    ]
    run(cmd)
    return dest


def contact_sheet(images: list[np.ndarray], cols: int = 3) -> np.ndarray:
    if not images:
        raise RuntimeError("No images for contact sheet")
    h, w = images[0].shape[:2]
    rows = (len(images) + cols - 1) // cols
    sheet = np.zeros((rows * h, cols * w, 3), dtype=np.uint8)
    for i, im in enumerate(images):
        if im.shape[0] != h or im.shape[1] != w:
            im = cv2.resize(im, (w, h))
        r, c = divmod(i, cols)
        sheet[r * h:(r + 1) * h, c * w:(c + 1) * w] = im
    return sheet
