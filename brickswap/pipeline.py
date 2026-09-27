from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2

from . import comfy_client, composite, detect, ffmpeg_util
from .config import WORK_DIR, Settings, bundled_refs


def new_job(clip: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    root = WORK_DIR / f"{stamp}_{clip.stem[:40]}"
    for name in ("frames", "masks", "overlays", "gen", "comp", "out"):
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def pick_ref(settings: Settings) -> Path:
    candidates = [
        Path(settings.living_ref) if settings.living_ref else None,
        Path(settings.zombie_ref) if settings.zombie_ref else None,
        Path(settings.dog_ref) if settings.dog_ref else None,
    ]
    for p in candidates:
        if p and p.exists():
            return p
    refs = bundled_refs()
    for name in ("living_woman.jpg", "living_man.jpg", "zombie.jpg", "dog.jpg"):
        hit = refs / name
        if hit.exists():
            return hit
    raise RuntimeError("No reference still found. Set Living / Zombie / Dog in the GUI.")


def preview_masks(clip: Path, settings: Settings, progress=None):
    clip = Path(clip)
    root = new_job(clip)
    frames = ffmpeg_util.extract_frames(
        clip,
        root / "frames",
        fps=settings.target_fps,
        max_long=settings.max_long_side,
        start_sec=0.0,
        duration=settings.preview_seconds,
    )
    classes = detect.parse_classes(settings.detect_classes)
    masks, stats = detect.process_frames(
        frames,
        root / "masks",
        classes,
        settings.mask_pad,
        settings.protect_bottom,
        progress=progress,
    )
    overlays = []
    thumbs = []
    for i, (fp, mp) in enumerate(zip(frames, masks)):
        img = cv2.imread(str(fp))
        mask = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
        vis = detect.overlay(img, mask)
        dest = root / "overlays" / f"o_{i:06d}.png"
        cv2.imwrite(str(dest), vis)
        overlays.append(dest)
        if i % max(1, len(frames) // 6) == 0:
            thumbs.append(vis)
    sheet_path = root / "out" / "mask_sheet.png"
    if thumbs:
        sheet = ffmpeg_util.contact_sheet(thumbs)
        cv2.imwrite(str(sheet_path), sheet)
    movie = ffmpeg_util.write_video(overlays, root / "out" / "masks.mp4", settings.target_fps)
    hits = sum(1 for s in stats if s["hits"])
    closeups = sum(1 for s in stats if s["closeup"])
    summary = f"{hits}/{len(frames)} frames have a subject. close-ups={closeups}. job={root}"
    return sheet_path, movie, root, summary


def preview_five(clip: Path, settings: Settings, progress=None):
    clip = Path(clip)
    root = new_job(clip)
    frames = ffmpeg_util.extract_frames(
        clip,
        root / "frames",
        fps=settings.target_fps,
        max_long=settings.max_long_side,
        start_sec=0.0,
        duration=settings.preview_seconds,
    )
    classes = detect.parse_classes(settings.detect_classes)
    masks, _stats = detect.process_frames(
        frames,
        root / "masks",
        classes,
        settings.mask_pad,
        settings.protect_bottom,
        progress=progress,
    )
    first = cv2.imread(str(frames[0]))
    h, w = first.shape[:2]
    client = comfy_client.ComfyClient(settings.comfy_url)
    if not client.ok():
        overlays = []
        for i, (fp, mp) in enumerate(zip(frames, masks)):
            img = cv2.imread(str(fp))
            mask = cv2.imread(str(mp), cv2.IMREAD_GRAYSCALE)
            dest = root / "overlays" / f"o_{i:06d}.png"
            cv2.imwrite(str(dest), detect.overlay(img, mask))
            overlays.append(dest)
        movie = ffmpeg_util.write_video(overlays, root / "out" / "preview.mp4", settings.target_fps)
        return movie, root, "ComfyUI is down. Wrote a red-mask preview instead."

    missing = client.has_nodes(["WanAnimateToVideo", "VHS_LoadVideo", "UNETLoader"])
    if missing:
        raise RuntimeError(
            "ComfyUI is missing: " + ", ".join(missing) +
            ". Load the official Wan 2.2 Animate workflow once so those nodes exist."
        )

    ref = pick_ref(settings)
    uploaded = client.upload_image(ref)
    ref_name = uploaded.get("name") or ref.name
    preview_clip = root / "out" / "src_preview.mp4"
    ffmpeg_util.write_video(frames, preview_clip, settings.target_fps)

    graph = comfy_client.build_animate_prompt(
        positive=settings.prompt,
        negative=settings.negative,
        video_name=preview_clip.name,
        ref_name=ref_name,
        width=w,
        height=h,
        length=len(frames),
        steps=settings.steps,
        cfg=settings.cfg,
        seed=settings.seed,
        use_lora=settings.use_speed_lora,
    )
    if progress:
        progress(0, 1, "queued in ComfyUI")
    pid = client.queue(graph)
    hist = client.wait(pid, progress=progress)
    images = []
    for node in (hist.get("outputs") or {}).values():
        for im in node.get("images") or []:
            dest = root / "gen" / im["filename"]
            client.download_output(im["filename"], dest, im.get("subfolder", ""), im.get("type", "output"))
            images.append(dest)
    if not images:
        raise RuntimeError("ComfyUI finished with no images")

    gen_dir = root / "gen"
    comps = composite.composite_folder(gen_dir, frames, masks, root / "comp", settings.mask_feather)
    movie = ffmpeg_util.write_video(comps or frames, root / "out" / "preview.mp4", settings.target_fps)
    try:
        ffmpeg_util.mux_audio(movie, clip, root / "out" / "preview_audio.mp4", 0.0, settings.preview_seconds)
        movie = root / "out" / "preview_audio.mp4"
    except Exception:
        pass
    return movie, root, f"preview ready: {movie}"
