import pickle
import os
import sys

plugin_loc = os.path.join(os.path.dirname(os.path.realpath(__file__)), "openvino_common")
sys.path.extend([plugin_loc])

import cv2
from superes_run_ov import run
import torch
from gimpml.tools.tools_utils import get_weight_path
import traceback
import numpy as np

def get_sr(img,s, model_name="sr_1033", weight_path=None,device="CPU"):
    if weight_path is None:
        weight_path = get_weight_path()
    
    if model_name == "esrgan":
        out = run(img, os.path.join(weight_path, "superresolution-ov", "realesrgan.xml"), device, model_name)
        out = cv2.resize(out, (0, 0), fx=s / 4, fy=s / 4)
    elif model_name == "edsr":
        b, g, r = cv2.split(np.array(img))
        channel_list = [b, g, r]
        output_list = []
        for img_c in channel_list:
            output = run(img_c, os.path.join(weight_path, "superresolution-ov", "edsr_mtl.xml"), device, model_name)
            output_list.append(output)
        out = cv2.merge([output_list[0], output_list[1], output_list[2]], 3)
        out = cv2.resize(out, (0, 0), fx=s / 2, fy=s / 2)

    else:
        out = run(img, os.path.join(weight_path, "superresolution-ov", "single-image-super-resolution-1033.xml"), device, model_name)
        out = cv2.resize(out, (0, 0), fx=s / 3, fy=s / 3)
    return out


if __name__ == "__main__":
    weight_path = get_weight_path()
    with open(os.path.join(weight_path, "..", "gimp_ml_run.pkl"), "rb") as file:
        data_output = pickle.load(file)

    device = data_output["device_name"]
    s = data_output["scale"]
    model_name = data_output["model_name"]


    image = cv2.imread(os.path.join(weight_path, "..", "cache.png"))[:, :, ::-1]
    try:
        output = get_sr(image, s, model_name=model_name, weight_path=weight_path, device=device)
        cv2.imwrite(os.path.join(weight_path, "..", "cache.png"), output[:, :, ::-1])
        with open(os.path.join(weight_path, "..", "gimp_ml_run.pkl"), "wb") as file:
            pickle.dump({"inference_status": "success", "device_name": device }, file)

        # Remove old temporary error files that were saved
        my_dir = os.path.join(weight_path, "..")
        for f_name in os.listdir(my_dir):
            if f_name.startswith("error_log"):
                os.remove(os.path.join(my_dir, f_name))

    except Exception as error:
        with open(os.path.join(weight_path, "..", "gimp_ml_run.pkl"), "wb") as file:
            pickle.dump({"inference_status": "failed"}, file)
        with open(os.path.join(weight_path, "..", "error_log.txt"), "w") as file:
            e_type, e_val, e_tb = sys.exc_info()
            traceback.print_exception(e_type, e_val, e_tb, file=file)
