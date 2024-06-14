import logging
import time
import sys
import random
import cv2
import argparse
import os
import json
import numpy as np
from gimpopenvino.tools.tools_utils import get_weight_path

from PIL import Image
from diffusers.schedulers import DDIMScheduler, LMSDiscreteScheduler, LCMScheduler, EulerDiscreteScheduler
plugin_loc = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..","..","gimpopenvino","tools","openvino_common")
sys.path.extend([plugin_loc])


from models_ov.stable_diffusion_engine import StableDiffusionEngineAdvanced, StableDiffusionEngine, LatentConsistencyEngine, StableDiffusionEngineReferenceOnly

logging.basicConfig(format='[ %(levelname)s ] %(message)s', level=logging.INFO, stream=sys.stdout) 
log = logging.getLogger()

def parse_args() -> argparse.Namespace:
    """Parse and return command line arguments."""
    parser = argparse.ArgumentParser(add_help=False)
    args = parser.add_argument_group('Options')
    args.add_argument('-h', '--help', action = 'help',
                      help='Show this help message and exit.')
    args.add_argument('-m', '--model_name',type = str, default = "sd_1.5_square_int8", required = False,
                      help='Optional. Modle path of directory. Default is sd_1.5_square_int8.')
    args.add_argument('-td','--text_device',type = str, default = 'GPU', required = False,
                      help='Optional. Specify the target device to infer on; CPU, GPU, NPU '
                      'is acceptable for Text encoder. Default value is GPU.')
    args.add_argument('-ud','--unet_device',type = str, default = 'GPU', required = False,
                      help='Optional. Specify the target device to infer on; CPU, GPU, NPU '
                      'is acceptable for Unet. Default value is GPU.')
    args.add_argument('-und','--unet_neg_device',type = str, default = 'NPU', required = False,
                      help='Optional. Specify the target device to infer on; CPU, GPU, NPU '
                      'is acceptable for Unet Negative. Default value is NPU.')
    args.add_argument('-vd','--vae_device',type = str, default = 'GPU', required = False,
                      help='Optional. Specify the target device to infer on; CPU, GPU, NPU '
                      'is acceptable for VAE decoder and encoder. Default value is GPU.')
    args.add_argument('-seed','--seed',type = int, default = None, required = False,
                      help='Optional. Specify the seed for initialize latent space.')
    args.add_argument('-niter','--iterations',type = int, default = 20, required = False,
                      help='Optional. Iterations for Stable diffusion.')
    args.add_argument('-si','--save_image',action='store_true', help='Optional. Save output image.')
    args.add_argument('-n','--num_images',type = int, default = 1, required = False,
                      help='Optional. Number of images to generate.')
    args.add_argument('-pm','--power_mode',type = str, default = None, required = False,
                      help='Optional. Specify the power mode.')
    

    
    return parser.parse_args()


def initialize_engine(model_name, model_path, device_list):
    if model_name == "sd_1.5_square_int8":
        log.info('Device list: %s', device_list)
        return StableDiffusionEngineAdvanced(model=model_path, device=device_list)
    if model_name == "sd_3.0_square_int8" or model_name == "sd_3.0_square_int4":
        log.info('Device list: %s', device_list)
        return StableDiffusionThreeEngine(model=model_path, device=device_list)
    if model_name == "sd_1.5_inpainting":
        return StableDiffusionEngineInpainting(model=model_path, device=device_list)
    if model_name == "sd_1.5_square_lcm":
        return LatentConsistencyEngine(model=model_path, device=device_list)
    if model_name == "sd_1.5_inpainting_int8":
        log.info('Advanced Inpainting Device list: %s', device_list)
        return StableDiffusionEngineInpaintingAdvanced(model=model_path, device=device_list)
    if model_name == "controlnet_openpose_int8":
        log.info('Device list: %s', device_list)
        return ControlNetOpenPoseAdvanced(model=model_path, device=device_list)
    if model_name == "controlnet_canny_int8":
        log.info('Device list: %s', device_list)
        return ControlNetCannyEdgeAdvanced(model=model_path, device=device_list)
    if model_name == "controlnet_scribble_int8":
        log.info('Device list: %s', device_list)
        return ControlNetScribbleAdvanced(model=model_path, device=device_list)
    if model_name == "controlnet_canny":
        return ControlNetCannyEdge(model=model_path, device=device_list)
    if model_name == "controlnet_scribble":
        return ControlNetScribble(model=model_path, device=device_list)
    if model_name == "controlnet_openpose":
        return ControlNetOpenPose(model=model_path, device=device_list)
    if model_name == "controlnet_referenceonly":
        return StableDiffusionEngineReferenceOnly(model=model_path, device=device_list)
    return StableDiffusionEngine(model=model_path, device=device_list)



def main():
    args = parse_args()
    results = []
    weight_path = get_weight_path()
    
    model_paths = {
        "sd_1.4": ["stable-diffusion-ov", "stable-diffusion-1.4"],
        "sd_1.5_square_lcm": ["stable-diffusion-ov", "stable-diffusion-1.5", "square_lcm"],
        "sd_1.5_portrait": ["stable-diffusion-ov", "stable-diffusion-1.5", "portrait"],
        "sd_1.5_square": ["stable-diffusion-ov", "stable-diffusion-1.5", "square"],
        "sd_1.5_square_int8": ["stable-diffusion-ov", "stable-diffusion-1.5", "square_int8"],
        "sd_1.5_landscape": ["stable-diffusion-ov", "stable-diffusion-1.5", "landscape"],
        "sd_1.5_portrait_512x768": ["stable-diffusion-ov", "stable-diffusion-1.5", "portrait_512x768"],
        "sd_1.5_landscape_768x512": ["stable-diffusion-ov", "stable-diffusion-1.5", "landscape_768x512"],
        "sd_1.5_inpainting": ["stable-diffusion-ov", "stable-diffusion-1.5", "inpainting"],
        "sd_1.5_inpainting_int8": ["stable-diffusion-ov", "stable-diffusion-1.5", "inpainting_int8"],
        "sd_2.1_square_base": ["stable-diffusion-ov", "stable-diffusion-2.1", "square_base"],
        "sd_2.1_square": ["stable-diffusion-ov", "stable-diffusion-2.1", "square"],
        "sd_3.0_square_int8": ["stable-diffusion-ov", "stable-diffusion-3.0", "square_int8"],
        "sd_3.0_square_int4": ["stable-diffusion-ov", "stable-diffusion-3.0", "square_int4"],
        "controlnet_referenceonly": ["stable-diffusion-ov", "controlnet-referenceonly"],
        "controlnet_openpose": ["stable-diffusion-ov", "controlnet-openpose"],
        "controlnet_canny": ["stable-diffusion-ov", "controlnet-canny"],
        "controlnet_scribble": ["stable-diffusion-ov", "controlnet-scribble"],
        "controlnet_openpose_int8": ["stable-diffusion-ov", "controlnet-openpose-int8"],
        "controlnet_canny_int8": ["stable-diffusion-ov", "controlnet-canny-int8"],
        "controlnet_scribble_int8": ["stable-diffusion-ov", "controlnet-scribble-int8"],
    }
    model_name = args.model_name
    model_path = os.path.join(weight_path, *model_paths.get(model_name))    
    model_config_file_name = os.path.join(model_path, "config.json")
    
    try:
        if args.power_mode is not None and os.path.exists(model_config_file_name):
            with open(model_config_file_name, 'r') as file:
                model_config = json.load(file)
                if model_config['power modes supported'].lower() == "yes":
                    execution_devices = model_config[args.power_mode.lower()]
                else:
                    execution_devices = model_config['best performance']
        else:
            execution_devices = [args.text_device, args.unet_device, args.unet_neg_device, args.vae_device]
        

    except (KeyError, FileNotFoundError, json.JSONDecodeError) as e:
        log.error(f"Error loading configuration: {e}. Only CPU will be used.")


    log.info('Initializing Inference Engine...') 
    log.info('Model Path: %s',model_path ) 
    log.info('Run models on: %s',execution_devices) 
    
    prompt = "a beautiful artwork illustration, concept art sketch of an astronaut in white futuristic cybernetic armor in a dark cave, volumetric fog, godrays, high contrast, vibrant colors, vivid colors, high saturation, by Greg Rutkowski and Jesper Ejsing and Raymond Swanland and alena aenami, featured on artstation, wide angle, vertical orientation" 
    negative_prompt = "lowres, bad quality, monochrome, cropped head, deformed face, bad anatomy" 
    
    init_image = None 
    num_infer_steps = args.iterations 
    guidance_scale = 8.0 
    strength = 1.0
    seed = 4294967294   
    
    scheduler = EulerDiscreteScheduler( 
                    beta_start=0.00085,  
                    beta_end=0.012,  
                    beta_schedule="scaled_linear" 
    ) 
    
    engine = initialize_engine(model_name=model_name, model_path=model_path, device_list=execution_devices)


    for i in range(0,args.num_images):
        log.info('Starting inference...') 
        log.info('Prompt: %s',prompt) 
        log.info('negative_prompt: %s',negative_prompt) 
        log.info('num_inference_steps: %s',num_infer_steps) 
        log.info('guidance_scale: %s',guidance_scale) 
        log.info('strength: %s',strength) 
        log.info('init_image: %s',init_image) 
    
        if args.seed:
            ran_seed = args.seed
        else:
            ran_seed = random.randrange(seed) #4294967294
        np.random.seed(int(ran_seed)) 
    
        log.info('Random Seed: %s',ran_seed)
        progress_callback = conn = None
        create_gif = False
        
        start_time = time.time()
        
        if model_name == "sd_1.5_inpainting" or model_name == "sd_1.5_inpainting_int8":
            output = engine(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=Image.open(os.path.join(weight_path, "..", "cache1.png")),
                mask_image=Image.open(os.path.join(weight_path, "..", "cache0.png")),
                scheduler=scheduler,
                strength=strength,
                num_inference_steps=num_infer_steps,
                guidance_scale=guidance_scale,
                eta=0.0,
                create_gif=bool(create_gif),
                model=model_path,
                callback=progress_callback,
                callback_userdata=conn
            )
        elif model_name == "controlnet_referenceonly":
            output = engine(
                prompt=prompt,
                negative_prompt=negative_prompt,
                init_image=Image.open(init_image),
                scheduler=scheduler,
                num_inference_steps=num_infer_steps,
                guidance_scale=guidance_scale,
                eta=0.0,
                create_gif=bool(create_gif),
                model=model_path,
                callback=progress_callback,
                callback_userdata=conn
            )
        elif "controlnet" in model_name: 
            output = engine(
                prompt=prompt,
                negative_prompt=negative_prompt,
                image=Image.open(init_image),
                scheduler=scheduler,
                num_inference_steps=num_infer_steps,
                guidance_scale=guidance_scale,
                eta=0.0,
                create_gif=bool(create_gif),
                model=model_path,
                callback=progress_callback,
                callback_userdata=conn
            )
       
        elif model_name == "sd_1.5_square_lcm":
            scheduler = LCMScheduler(
                beta_start=0.00085,
                beta_end=0.012,
                beta_schedule="scaled_linear"
            )
            output = engine(
                prompt=prompt,
                num_inference_steps=num_infer_steps,
                guidance_scale=guidance_scale,
                scheduler=scheduler,
                lcm_origin_steps=50,
                model=model_path,
                callback=progress_callback,
                callback_userdata=conn,
                seed=seed
            )
        elif "sd_3.0" in model_name:
            output = engine(
                    prompt = prompt,
                    negative_prompt = negative_prompt,
                    num_inference_steps = num_infer_steps,
                    guidance_scale = guidance_scale,
                    callback = progress_callback,
                    callback_userdata = conn,
                    seed = seed
            )        
        else:
            if model_name == "sd_2.1_square":
                scheduler = EulerDiscreteScheduler(
                    beta_start=0.00085,
                    beta_end=0.012,
                    beta_schedule="scaled_linear",
                    prediction_type="v_prediction"
                )
            model = model_path
            if "sd_2.1" in model_name:
                model = model_name

            output = engine(
                prompt=prompt,
                negative_prompt=negative_prompt,
                init_image=None if init_image is None else Image.open(init_image),
                scheduler=scheduler,
                strength=strength,
                num_inference_steps=num_infer_steps,
                guidance_scale=guidance_scale,
                eta=0.0,
                create_gif=bool(create_gif),
                model=model,
                callback=progress_callback,
                callback_userdata=conn
            )
        
        print ("Process time: ", time.time() - start_time)

        results.append([output,"sd_result" + 
            "_" + execution_devices[0] + 
            "_" + execution_devices[1] + 
            "_" + execution_devices[2] + 
            "_" + execution_devices[3] + 
            "_" + str(ran_seed) + 
            "_" + str(num_infer_steps) +  "_steps" +".jpg"])
        
    if args.save_image:
        for result in results:
            cv2.imwrite(result[1], result[0]) 
    
if __name__ == "__main__":
    sys.exit(main())

