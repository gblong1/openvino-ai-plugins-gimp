from enum import Enum
from typing import Any

from constants import LCM_DEFAULT_MODEL, LCM_DEFAULT_MODEL_OPENVINO
from paths import FastStableDiffusionPaths
from PIL import Image
from pydantic import BaseModel


class LCMLora(BaseModel):
    base_model_id: str = "Lykon/dreamshaper-8"
    lcm_lora_id: str = "latent-consistency/lcm-lora-sdv1-5"


class DiffusionTask(str, Enum):
    """Diffusion task types"""

    text_to_image = "text_to_image"
    image_to_image = "image_to_image"


class Lora(BaseModel):
    models_dir: str = FastStableDiffusionPaths.get_lora_models_path()
    path: Any | None = None
    weight: float | None = 0.5
    fuse: bool = True
    enabled: bool = False


class ControlNetSetting(BaseModel):
    adapter_path: str | None = None  # ControlNet adapter path
    conditioning_scale: float = 0.5
    enabled: bool = False
    _control_image: Image = None  # Control image, PIL image


class GGUFModel(BaseModel):
    gguf_models: str = FastStableDiffusionPaths.get_gguf_models_path()
    diffusion_path: str | None = None
    clip_path: str | None = None
    t5xxl_path: str | None = None
    vae_path: str | None = None


class LCMDiffusionSetting(BaseModel):
    lcm_model_id: str = LCM_DEFAULT_MODEL
    openvino_lcm_model_id: str = LCM_DEFAULT_MODEL_OPENVINO
    use_offline_model: bool = False
    use_lcm_lora: bool = False
    lcm_lora: LCMLora | None = LCMLora()
    use_tiny_auto_encoder: bool = False
    use_openvino: bool = False
    prompt: str = ""
    negative_prompt: str = ""
    init_image: Any = None
    strength: float | None = 0.6
    image_height: int | None = 512
    image_width: int | None = 512
    inference_steps: int | None = 1
    guidance_scale: float | None = 1
    clip_skip: int | None = 1
    token_merging: float | None = 0
    number_of_images: int | None = 1
    seed: int | None = 123123
    use_seed: bool = False
    use_safety_checker: bool = False
    diffusion_task: str = DiffusionTask.text_to_image.value
    lora: Lora | None = Lora()
    controlnet: ControlNetSetting | list[ControlNetSetting] | None = None
    dirs: dict = {
        "controlnet": FastStableDiffusionPaths.get_controlnet_models_path(),
        "lora": FastStableDiffusionPaths.get_lora_models_path(),
    }
    rebuild_pipeline: bool = False
    use_gguf_model: bool = False
    gguf_model: GGUFModel | None = GGUFModel()
