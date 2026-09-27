# Workflows

BrickSwap talks to a running ComfyUI at http://127.0.0.1:8188.

The app builds an API graph that uses `WanAnimateToVideo` in Mix mode:
reference minifig + source clip + subject mask / background.

If Check setup reports missing nodes, load the official Comfy-Org
Wan 2.2 Animate workflow inside ComfyUI first so those classes exist:

https://docs.comfy.org/tutorials/video/wan/wan2-2-animate

Mix mode = replace the person in the video with the reference character.
That is the mode BrickSwap wants. Do not disconnect background / mask
(that would be Move mode, which animates the still on its own backdrop).
