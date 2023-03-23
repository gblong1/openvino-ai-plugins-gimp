"""
Copyright(C) 2022-2023 Intel Corporation
SPDX - License - Identifier: Apache - 2.0

"""



from .model import Model



import inspect
import numpy as np
# openvino
from openvino.runtime import Core
# tokenizer
from transformers import CLIPTokenizer
# utils
from tqdm import tqdm

from diffusers import LMSDiscreteScheduler, PNDMScheduler
import cv2
import os
import sys

import transformers

#For GIF
from PIL import Image
import glob
import json



def result(var):
    return next(iter(var.values()))


class StableDiffusionEngine:
    def __init__(
            self,
            scheduler,
            model="bes-dev/stable-diffusion-v1-4-openvino",
            tokenizer="openai/clip-vit-large-patch14",
            device="CPU"
            ):
        #self.tokenizer = CLIPTokenizer.from_pretrained(tokenizer)
        self.tokenizer = CLIPTokenizer.from_pretrained(model,local_files_only=True)
        self.scheduler = scheduler
        # models
        #print("weight_path in engine ", model)
        #print("Final path:", os.path.join(model, "text_encoder.xml"))
        self.core = Core()
        self.core.set_property({'CACHE_DIR': os.path.join(model, 'cache')}) #adding caching to reduce init time
        # text features
        self._text_encoder = self.core.read_model(os.path.join(model, "text_encoder.xml"), os.path.join(model, "text_encoder.bin"))
         
        self.text_encoder = self.core.compile_model(self._text_encoder, device)
        # diffusion
        self._unet = self.core.read_model(os.path.join(model, "unet.xml"),os.path.join(model, "unet.bin"))
  
   
        self.unet = self.core.compile_model(self._unet, device)
        self.latent_shape = tuple(self._unet.inputs[0].shape)[1:]
        # decoder
        self._vae_decoder = self.core.read_model(os.path.join(model, "vae_decoder.xml"), os.path.join(model, "vae_decoder.bin"))
       
        self.vae_decoder = self.core.compile_model(self._vae_decoder, device)
        # encoder
        self._vae_encoder = self.core.read_model(os.path.join(model, "vae_encoder.xml"), os.path.join(model, "vae_encoder.bin")) 

        self.vae_encoder = self.core.compile_model(self._vae_encoder, device)
        self.init_image_shape = tuple(self._vae_encoder.inputs[0].shape)[2:]

    def _preprocess_mask(self, mask):
        h, w = mask.shape
        if h != self.init_image_shape[0] and w != self.init_image_shape[1]:
            mask = cv2.resize(
                mask,
                (self.init_image_shape[1], self.init_image_shape[0]),
                interpolation = cv2.INTER_NEAREST
            )
        mask = cv2.resize(
            mask,
            (self.init_image_shape[1] // 8, self.init_image_shape[0] // 8),
            interpolation = cv2.INTER_NEAREST
        )
        mask = mask.astype(np.float32) / 255.0
        mask = np.tile(mask, (4, 1, 1))
        mask = mask[None].transpose(0, 1, 2, 3)
        mask = 1 - mask
        return mask

    def _preprocess_image(self, image):
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        h, w = image.shape[1:]
        if h != self.init_image_shape[0] and w != self.init_image_shape[1]:
            image = cv2.resize(
                image,
                (self.init_image_shape[1], self.init_image_shape[0]),
                interpolation=cv2.INTER_LANCZOS4
            )
        # normalize
        image = image.astype(np.float32) / 255.0
        image = 2.0 * image - 1.0
        # to batch
        image = image[None].transpose(0, 3, 1, 2)
        return image

    def _encode_image(self, init_image):
        moments = result(self.vae_encoder.infer_new_request({
            "init_image": self._preprocess_image(init_image)
        }))
        mean, logvar = np.split(moments, 2, axis=1)
        std = np.exp(logvar * 0.5)
        latent = (mean + std * np.random.randn(*mean.shape)) * 0.18215
        return latent

    def __call__(
            self,
            prompt,
            init_image = None,
            mask = None,
            strength = 0.5,
            num_inference_steps = 32,
            guidance_scale = 7.5,
            eta = 0.0,
            create_gif = False,
            model = None
    ):
        # extract condition
        tokens = self.tokenizer(
            prompt,
            padding="max_length",
            max_length=self.tokenizer.model_max_length,
            truncation=True
        ).input_ids
        text_embeddings = result(
            self.text_encoder.infer_new_request({"tokens": np.array([tokens])})
        )

        # do classifier free guidance
        if guidance_scale > 1.0:
            tokens_uncond = self.tokenizer(
                "",
                padding="max_length",
                max_length=self.tokenizer.model_max_length,
                truncation=True
            ).input_ids
            uncond_embeddings = result(
                self.text_encoder.infer_new_request({"tokens": np.array([tokens_uncond])})
            )
            text_embeddings = np.concatenate((uncond_embeddings, text_embeddings), axis=0)

        # set timesteps
        accepts_offset = "offset" in set(inspect.signature(self.scheduler.set_timesteps).parameters.keys())
        extra_set_kwargs = {}
        offset = 0
        if accepts_offset:
            offset = 1
            extra_set_kwargs["offset"] = 1

        self.scheduler.set_timesteps(num_inference_steps, **extra_set_kwargs)

        # initialize latent latent
        if init_image is None:
            latents = np.random.randn(*self.latent_shape)
            init_timestep = num_inference_steps
        else:
            init_latents = self._encode_image(init_image)
            init_timestep = int(num_inference_steps * strength) + offset
            init_timestep = min(init_timestep, num_inference_steps)
            timesteps = np.array([[self.scheduler.timesteps[-init_timestep]]]).astype(np.long)
            noise = np.random.randn(*self.latent_shape)
            latents = self.scheduler.add_noise(init_latents, noise, timesteps)[0]

        if init_image is not None and mask is not None:
            mask = self._preprocess_mask(mask)
        else:
            mask = None

        # if we use LMSDiscreteScheduler, let's make sure latents are mulitplied by sigmas
        if isinstance(self.scheduler, LMSDiscreteScheduler):
            latents = latents * self.scheduler.sigmas[0]

        # prepare extra kwargs for the scheduler step, since not all schedulers have the same signature
        # eta (η) is only used with the DDIMScheduler, it will be ignored for other schedulers.
        # eta corresponds to η in DDIM paper: https://arxiv.org/abs/2010.02502
        # and should be between [0, 1]
        accepts_eta = "eta" in set(inspect.signature(self.scheduler.step).parameters.keys())
        extra_step_kwargs = {}
        if accepts_eta:
            extra_step_kwargs["eta"] = eta

        t_start = max(num_inference_steps - init_timestep + offset, 0)
        
        if create_gif:
            frames = []
        
        for i, t in tqdm(enumerate(self.scheduler.timesteps[t_start:])):
            # expand the latents if we are doing classifier free guidance
            latent_model_input = np.stack([latents, latents], 0) if guidance_scale > 1.0 else latents[None]
            if isinstance(self.scheduler, LMSDiscreteScheduler):
                sigma = self.scheduler.sigmas[i]
                latent_model_input = latent_model_input / ((sigma**2 + 1) ** 0.5)

            # predict the noise residual
            noise_pred = result(self.unet.infer_new_request({
                "latent_model_input": latent_model_input,
                "t": float(t),
                "encoder_hidden_states": text_embeddings
            }))

            # perform guidance
            if guidance_scale > 1.0:
                noise_pred = noise_pred[0] + guidance_scale * (noise_pred[1] - noise_pred[0])

            # compute the previous noisy sample x_t -> x_t-1
            if isinstance(self.scheduler, LMSDiscreteScheduler):
                latents = self.scheduler.step(noise_pred, i, latents, **extra_step_kwargs)["prev_sample"]
            else:
                latents = self.scheduler.step(noise_pred, t, latents, **extra_step_kwargs)["prev_sample"]

            # masking for inapinting
            if mask is not None:
                init_latents_proper = self.scheduler.add_noise(init_latents, noise, t)
                latents = ((init_latents_proper * mask) + (latents * (1 - mask)))[0]
            if create_gif:
                frames.append(latents)            

        image = result(self.vae_decoder.infer_new_request({
            "latents": np.expand_dims(latents, 0)
        }))

        # convert tensor to opencv's image format
        image = (image / 2 + 0.5).clip(0, 1)
        image = (image[0].transpose(1, 2, 0)[:, :, ::-1] * 255).astype(np.uint8)
        if create_gif:
            gif_folder=os.path.join(model,"../../gif")
            if not os.path.exists(gif_folder):
                os.makedirs(gif_folder)
            for i in range(0,len(frames)):
                image = result(self.vae_decoder.infer_new_request({
                "latents": np.expand_dims(frames[i], 0)}))
                image = (image / 2 + 0.5).clip(0, 1)
                image = (image[0].transpose(1, 2, 0)[:, :, ::-1] * 255).astype(np.uint8)
                output = gif_folder + "/" + str(i).zfill(3) +".png"
                cv2.imwrite(output, image)
            with open(os.path.join(gif_folder, "prompt.json"), "w") as file:
                json.dump({"prompt": prompt}, file)
            frames_image =  [Image.open(image) for image in glob.glob(f"{gif_folder}/*.png")]  
            frame_one = frames_image[0]
            gif_file=os.path.join(gif_folder,"stable_diffusion.gif")
            frame_one.save(gif_file, format="GIF", append_images=frames_image, save_all=True, duration=100, loop=0)

        return image