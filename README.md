# BrickSwap

Replace people, zombies, and dogs in a real clip with LEGO minifigures.
The room, camera, and burned-in captions stay yours.

This is a **character swap**, not a whole-frame restyle.

1. Find the subjects (YOLO-seg; zombies count as people).
2. Grow the mask so a minifig head has room.
3. Protect the subtitle band.
4. Drive **Wan 2.2 Animate Mix** with a minifig still plus `background_video` and `character_mask`.
5. Composite the generated figure back onto the untouched plate.

Mix keeps the original scene. Move invents a new one. BrickSwap is Mix only.

## Tomorrow morning — not a full episode

1. Clone and install.
2. Open a 5–10 second clip.
3. Click **Preview masks**. Red overlay on people only, captions left alone.
4. Start ComfyUI with the Wan 2.2 Animate template loaded once.
5. Click **Check setup**, then **Preview 5 seconds**.
6. Stop if it still looks like a human-shaped toy.

## Install (Windows, RTX 4060)

```bat
git clone https://github.com/evilgenius79/BrickSwap.git C:\BrickSwap
cd C:\BrickSwap
install.bat
```

Mask preview does not need ComfyUI. Generation does.

### ComfyUI models

https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/tree/main/split_files

```
ComfyUI/models/
  diffusion_models/Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors
  loras/lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors
  text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors
  clip_visions/clip_vision_h.safetensors
  vae/wan_2.1_vae.safetensors
```

Custom nodes: ComfyUI-Manager, comfyui_controlnet_aux, ComfyUI-KJNodes, ComfyUI-VideoHelperSuite.

Load the official template **Wan2.2 Animate** once so the node classes exist, then use BrickSwap.
On an 8 GB 4060 keep the long side at 480–512 and leave Speed LoRA on.

## Reference stills

`refs/` should contain living_woman, living_man, zombie, and dog product shots.
The download zip in the Grok project includes those JPEGs. Git keeps only the README here.

## Jobs

`%USERPROFILE%\BrickSwap\jobs\`
