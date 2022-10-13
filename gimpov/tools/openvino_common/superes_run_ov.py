"""
 Copyright (C) 2018-2022 Intel Corporation

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import logging
import sys
from argparse import ArgumentParser, SUPPRESS
from pathlib import Path
from time import perf_counter


import cv2
from openvino.inference_engine import IECore

#sys.path.append(str(Path(__file__).resolve().parents[2] / 'common/python'))

from  models_ov.SuperResolution import SuperResolution
from performance_metrics import PerformanceMetrics
from pipelines import get_user_config, AsyncPipeline
import monitors
from images_capture import open_images_capture


logging.basicConfig(format='[ %(levelname)s ] %(message)s', level=logging.DEBUG, stream=sys.stdout)
log = logging.getLogger()


def run(frame, model_path, device, model_name):
 
     log.info('Initializing Inference Engine...')
     ie = IECore()

     plugin_config = get_user_config(device, '', None)
     log.info('Loading network: %s',model_name)
     log.info('Device: %s',device)
     
     model = SuperResolution(ie, model_path, frame.shape, model_name)
     pipeline = AsyncPipeline(ie, model, plugin_config, device, 1)

     log.info('Starting inference...')

     if pipeline.is_ready():
        start_time = perf_counter()
        pipeline.submit_data(frame, 0, {'frame': frame, 'start_time': start_time})
     else:
                # Wait for empty request
        pipeline.await_any()

     if pipeline.callback_exceptions:
                raise pipeline.callback_exceptions[0]

     pipeline.await_all()
        # Process all completed requests
     results = pipeline.get_result(0)
     while results is None:
            log.info("WAIT for results")
     if results:
            log.info('We got some results')
           
            result_frame, frame_meta = results
            input_frame = frame_meta['frame']

            #if input_frame.shape != result_frame.shape:
            #    input_frame = cv2.resize(input_frame, (result_frame.shape[1], result_frame.shape[0]))
            #final_image = cv2.hconcat([input_frame, result_frame])
        
     return result_frame

if __name__ == "__main__":
    import numpy as np
    img = cv2.imread(r"D:\git\\GIMP-OV\testscases\sampleinput\haze.png") #[:, :, ::-1]

    #b, g, r = cv2.split(np.array(img))
    #channel_list = [b, g, r]
    #output_list = []
    #for img_c in channel_list:
    #    output = run(img_c, r"D:\git\31.93_psnr_optimized_edsr\optimized\edsr_mtl.xml","CPU","edsr")
    #    output_list.append(output)
    #mask = cv2.merge([output_list[0], output_list[1], output_list[2]], 3)

    mask = run(img, r"C:\Users\lab_admin\GIMP-OV\weights\superresolution-ov\realesrgan.xml","VPUX","esrgan") #r r'D:\optimized\realesrgan.xml''E:\open_model_zoo\models\intel\single-image-super-resolution-1033\FP16\single-image-super-resolution-1033.xml
 
    #print("type = ", type(mask))
    #print(mask.shape)
    cv2.imwrite("esrgan_ov.png", mask)