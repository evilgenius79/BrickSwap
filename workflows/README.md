# Workflows

BrickSwap talks to ComfyUI at http://127.0.0.1:8188.

Mix-mode graph around `WanAnimateToVideo`:

- `reference_image` — minifig still
- `clip_vision_output` — CLIP vision of that still
- `pose_video` / `background_video` — uploaded source clip
- `character_mask` — YOLO mask via ImageToMask

https://docs.comfy.org/built-in-nodes/WanAnimateToVideo.md
https://docs.comfy.org/tutorials/video/wan/wan2-2-animate

Do not disconnect background_video or character_mask. That is Move mode.
