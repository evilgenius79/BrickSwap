# BrickSwap

Replace people, zombies, and dogs in a real clip with LEGO minifigures.
The room, camera, and burned-in captions stay yours.

This is a character-swap pipeline, not a whole-frame restyle:

1. Find subjects (YOLO-seg; zombies count as people).
2. Grow the mask so a minifig head has room.
3. Protect the subtitle band.
4. Drive Wan 2.2 Animate Mix with a minifig reference still.
5. Composite the generated figure back onto the untouched plate.

## First, not a full episode

1. Install.
2. Open a clip.
3. Preview masks — red overlay on people only.
4. Start ComfyUI with Wan 2.2 Animate.
5. Preview 5 seconds.
6. Stop if it still looks like a human-shaped toy.

## Install (Windows, RTX 4060)

```bat
winget install --id Gyan.FFmpeg -e --accept-package-agreements
winget install --id Python.Python.3.12 -e --accept-package-agreements
cd C:\BrickSwap
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run.py
```

Or run `install.bat`.

Mask preview works without ComfyUI. Generation needs Wan 2.2 Animate models and custom nodes (see workflows/README.md).
