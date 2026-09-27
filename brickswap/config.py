from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

APP_NAME = "BrickSwap"
SETTINGS_DIR = Path.home() / "BrickSwap"
SETTINGS_PATH = SETTINGS_DIR / "settings.json"
WORK_DIR = SETTINGS_DIR / "jobs"

DEFAULT_DETECT = "person,dog,cat"
DEFAULT_PROMPT = (
    "official LEGO minifigure, yellow cylindrical head with stud, printed face, "
    "no neck, C-shaped claw hands, short stubby block legs, glossy ABS plastic, "
    "keep the original clothing colors and hair style as printed LEGO decorations"
)
DEFAULT_NEGATIVE = (
    "photorealistic human, skin pores, realistic face, depth of field, "
    "deformed hands, extra limbs, text, watermark, zombie face on living person"
)


@dataclass
class Settings:
    comfy_url: str = "http://127.0.0.1:8188"
    detect_classes: str = DEFAULT_DETECT
    mask_pad: float = 0.08
    mask_feather: int = 7
    protect_bottom: float = 0.15
    closeup_area: float = 0.30
    preview_seconds: float = 5.0
    target_fps: int = 16
    max_long_side: int = 832
    steps: int = 4
    cfg: float = 1.0
    seed: int = 42
    prompt: str = DEFAULT_PROMPT
    negative: str = DEFAULT_NEGATIVE
    living_ref: str = ""
    zombie_ref: str = ""
    dog_ref: str = ""
    use_speed_lora: bool = True
    last_clip: str = ""

    def save(self) -> None:
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        SETTINGS_PATH.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls) -> "Settings":
        if not SETTINGS_PATH.exists():
            s = cls()
            s.save()
            return s
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


def bundled_refs() -> Path:
    return Path(__file__).resolve().parent.parent / "refs"
