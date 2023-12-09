import os
import requests
import json

import yaml

from tale.image_gen.base_gen import ImageGeneratorBase

class Automatic1111Interface(ImageGeneratorBase):
    """ Generating images using the AUTOMATIC1111 API (stable-diffusion-webui)"""


    def __init__(self, address: str = 'localhost', port: int = 7860) -> None:
        super().__init__("/sdapi/v1/txt2img", address, port)
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../../automatic1111_config.yaml")), "r") as stream:
            try:
                self.config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        print(self.config)
         

    def generate_image(self, prompt: str, save_path: str, image_name: str) -> bool:
        """Generate an image from text."""
        image_data = self.send_request(prompt + ', ' + self.config['ALWAYS_PROMPT'], self.config['NEGATIVE_PROMPT'], self.config['SEED'], self.config['SAMPLER'], self.config['STEPS'], self.config['CFG_SCALE'], self.config['WIDTH'], self.config['HEIGHT'])
        if image_data is None:
            return False
        self.convert_image(image_data, save_path, image_name)
        return True


    def send_request(self, prompt, negative_prompt: str = 'text, watermark', seed: int = -1, sampler: str = "Euler a", steps: int = 30, cfg_scale: int = 7, width: int = 512, height: int = 512) -> bytes:

        data = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "alwayson_scripts": {},
            "seed": seed,
            "sampler_index": sampler,
            "batch_size": 1,
            "n_iter": 1,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height,
            "restore_faces": False,
            "override_settings": {},
            "override_settings_restore_afterwards": True
        }
        response = requests.post(self.url, json=data)
        if response.status_code == 200:
            json_data = json.loads(response.content)
            return json_data['images'][0]
        else:
            try:
                error_data = response.json()
                print("Error:")
                print(str(error_data))
                
            except json.JSONDecodeError:
                print(f"Error: Unable to parse JSON error data.")
            return None