from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import requests


class ComfyError(RuntimeError):
    pass


class ComfyClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base = base_url.rstrip("/")
        self.client_id = str(uuid.uuid4())

    def ok(self) -> bool:
        try:
            r = requests.get(f"{self.base}/system_stats", timeout=3)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def object_info(self) -> dict:
        r = requests.get(f"{self.base}/object_info", timeout=20)
        r.raise_for_status()
        return r.json()

    def has_nodes(self, names: list[str]) -> list[str]:
        info = self.object_info()
        return [n for n in names if n not in info]

    def upload_image(self, path: Path, subfolder: str = "brickswap") -> dict:
        with path.open("rb") as fh:
            r = requests.post(
                f"{self.base}/upload/image",
                files={"image": (path.name, fh, "image/png")},
                data={"overwrite": "true", "subfolder": subfolder},
                timeout=60,
            )
        r.raise_for_status()
        return r.json()

    def free(self) -> None:
        try:
            requests.post(
                f"{self.base}/free",
                json={"unload_models": True, "free_memory": True},
                timeout=10,
            )
        except requests.RequestException:
            pass

    def queue(self, workflow: dict) -> str:
        payload = {"prompt": workflow, "client_id": self.client_id}
        r = requests.post(f"{self.base}/prompt", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise ComfyError(json.dumps(data["error"])[:2000])
        return data["prompt_id"]

    def wait(self, prompt_id: str, timeout: int = 3600, progress=None) -> dict:
        t0 = time.time()
        while time.time() - t0 < timeout:
            hist = requests.get(f"{self.base}/history/{prompt_id}", timeout=20).json()
            if prompt_id in hist:
                return hist[prompt_id]
            q = requests.get(f"{self.base}/queue", timeout=10).json()
            running = q.get("queue_running") or []
            pending = q.get("queue_pending") or []
            if progress:
                progress(0, 1, f"comfy running={len(running)} pending={len(pending)}")
            time.sleep(2)
        raise ComfyError("ComfyUI timed out")

    def interrupt(self) -> None:
        try:
            requests.post(f"{self.base}/interrupt", timeout=5)
        except requests.RequestException:
            pass

    def download_output(self, filename: str, dest: Path, subfolder: str = "", type_: str = "output") -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(
            f"{self.base}/view",
            params={"filename": filename, "subfolder": subfolder, "type": type_},
            timeout=120,
        )
        r.raise_for_status()
        dest.write_bytes(r.content)
        return dest


def build_animate_prompt(
    *,
    positive: str,
    negative: str,
    video_name: str,
    ref_name: str,
    width: int,
    height: int,
    length: int,
    steps: int,
    cfg: float,
    seed: int,
    use_lora: bool,
) -> dict:
    lora_name = "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
    unet = "Wan2_2-Animate-14B_fp8_e4m3fn_scaled_KJ.safetensors"
    graph = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "fp8_e4m3fn"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "4": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": positive}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": negative}},
        "7": {"class_type": "LoadImage", "inputs": {"image": ref_name}},
        "8": {
            "class_type": "VHS_LoadVideo",
            "inputs": {
                "video": video_name,
                "force_rate": 16,
                "custom_width": width,
                "custom_height": height,
                "skip_first_frames": 0,
                "select_every_nth": 1,
                "frame_load_cap": length,
            },
        },
    }
    model_out = ["1", 0]
    if use_lora:
        graph["9"] = {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {"model": ["1", 0], "lora_name": lora_name, "strength_model": 1.0},
        }
        model_out = ["9", 0]
    graph["10"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": model_out,
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": "euler",
            "scheduler": "simple",
            "positive": ["5", 0],
            "negative": ["6", 0],
            "latent_image": ["11", 2],
            "denoise": 1.0,
        },
    }
    graph["11"] = {
        "class_type": "WanAnimateToVideo",
        "inputs": {
            "positive": ["5", 0],
            "negative": ["6", 0],
            "vae": ["3", 0],
            "width": width,
            "height": height,
            "length": length,
            "clip_vision": ["4", 0],
            "reference_image": ["7", 0],
            "video": ["8", 0],
        },
    }
    graph["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["10", 0], "vae": ["3", 0]}}
    graph["13"] = {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": "brickswap"}}
    return graph
