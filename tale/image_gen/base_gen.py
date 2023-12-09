import json
import os
import requests
import io
import base64
from PIL import Image, PngImagePlugin


class ImageGeneratorBase():

    def __init__(self, endpoint: str, address: str = 'localhost', port: int = 7860) -> None:
        self.address = address
        self.port = port
        self.url = f"http://{self.address}:{self.port}{endpoint}"

    def convert_image(self, image_data: bytes, output_folder: str, image_name):
        image = Image.open(io.BytesIO(base64.b64decode(image_data)))
        path = os.path.join(output_folder, image_name + '.jpg')
        image.save(path)

    def generate_image(self, prompt: str, save_path: str, image_name: str) -> bool:
        pass