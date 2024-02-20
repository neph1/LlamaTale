import base64
import json

import os
import random
import time

import requests
import yaml
from .base_gen import ImageGeneratorBase

class ComfyUi(ImageGeneratorBase):
    """ Generating images using the COMFY_UI API (comfy-ui)"""

    sampler_id = "8"   
    
    def __init__(self, address: str = '127.0.0.1', port: int = 8188) -> None:
        super().__init__("/prompt", address, port)
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../../comfy_ui.yaml")), "r") as stream:
            try:
                self.config = yaml.safe_load(stream)
                self.generate_in_background = self.config['GENERATE_IN_BACKGROUND']
            except yaml.YAMLError as exc:
                print(exc)
    def generate_image(self, prompt: str, save_path: str, image_name: str) -> bool:
        """Generate an image from text."""
        image_data = self.send_request(prompt + ', ' + self.config['ALWAYS_PROMPT'], self.config['NEGATIVE_PROMPT'], self.config['SEED'], self.config['SAMPLER'], self.config['STEPS'], self.config['CFG_SCALE'], self.config['WIDTH'], self.config['HEIGHT'], self.config['SCHEDULER'], self.config['MODEL'])
        if image_data is None:
            return False
        self.convert_image(image_data[0], save_path, image_name)
        return True

    def send_request(self, prompt, negative_prompt: str, seed: int, sampler: str, steps: int, cfg_scale: int, width: int, height: int, scheduler: str = '', model: str = '') -> bytes:

        path = self._load_workflow('comfy_ui_workflow.json')
        with open(path) as f:
            workflow = json.load(f)

        if model:
            workflow = self.set_model(workflow, model)

        workflow = self._set_text_prompts(workflow, prompt, negative_prompt)

        workflow = self._set_sampler(workflow, sampler, cfg_scale, seed, steps, scheduler)
        workflow = self._set_image_size(workflow, width, height)

        p = {"prompt": workflow}
        response = requests.post(self.url, json=p)
        if not response.status_code == 200:
            try:
                error_data = response.json()
                print("Error:")
                print(str(error_data))
                
            except json.JSONDecodeError:
                print(f"Error: Unable to parse JSON error data.")
            return None
        
        json_data = json.loads(response.content)
        prompt_id = json_data['prompt_id']
        while not self.poll_queue(prompt_id):
            # pause the thread for 1 second
            time.sleep(1)
            self.lock = False
        return self.get_history(prompt_id)
        
    def get_history(self, prompt_id: str):
        response = requests.get(f"http://{self.address}:{self.port}/history", data=prompt_id)
        if response.status_code == 200:
            history = json.loads(response.content)
            history = history[prompt_id]
            output_images = {}
            for node_id in history['outputs']:
                node_output = history['outputs'][node_id]
                if 'images' in node_output:
                    images_output = []
                    for image in node_output['images']:
                        image_data = self.get_image(image['filename'], image['subfolder'], image['type'])
                        images_output.append(image_data)
                    output_images[node_id] = images_output
            return output_images[node_id]

    def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        headers = {"Content-Type": "image/png"}
        response = requests.get(f"http://{self.address}:{self.port}/view", params=data, headers=headers, stream=True)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode('utf-8')
        
    def poll_queue(self, prompt_id: str):    
        """ Return True if the prompt is not in the queue, False otherwise."""
        response = requests.get(f"http://{self.address}:{self.port}/queue")
        if response.status_code == 200:
            json_data = json.loads(response.content)
            for prompt in json_data['queue_pending']:
                if prompt[1] == prompt_id:
                    return False
            for prompt in json_data['queue_running']:
                if prompt[1] == prompt_id:
                    return False
        return True
        
    def set_model(self, data: dict, model: str):
        data["4"]["inputs"]["ckpt_name"] = model
        return data
    
    def _load_workflow(self, workflow: str) -> dict:
        file_path = os.path.join(os.path.dirname(__file__) + '/../../', workflow)
        return file_path
        
    def _set_text_prompts(self, data: dict, prompt: str, negative_prompt: str) -> dict:
        data["6"]["inputs"]["text"] = prompt
        data["7"]["inputs"]["text"] = negative_prompt
        return data
        
    def _set_sampler(self, data: dict, sampler: str, cfg: float, seed: int, steps: int, scheduler: str = '') -> dict:
        data["3"]["inputs"]["sampler_name"] = sampler.lower()
        data["3"]["inputs"]["cfg"] = cfg
        data["3"]["inputs"]["seed"] = random.randint(0, 18446744073709552000) if seed == -1 else seed
        print("seed", data["3"]["inputs"]["seed"])
        data["3"]["inputs"]["steps"] = steps
        if scheduler:
            data["3"]["inputs"]["scheduler"] = scheduler
        return data
    
    def _set_image_size(self, data: dict, width: int = 512, height: int = 512) -> dict:
        data["5"]["inputs"]["width"] = width
        data["5"]["inputs"]["height"] = height
        return data