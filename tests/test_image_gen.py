import json
import responses
from tale.image_gen.automatic1111 import Automatic1111Interface


class TestAutomatic():

    def test_image_gen_config(self):
        image_generator = Automatic1111Interface()
        assert image_generator.config['ALWAYS_PROMPT'] == 'closeup'
        assert image_generator.config['NEGATIVE_PROMPT'] == 'text, watermark, logo'
        assert image_generator.config['SEED'] == -1
        assert image_generator.config['SAMPLER'] == 'Euler'
        assert image_generator.config['STEPS'] == 30
        assert image_generator.config['CFG_SCALE'] == 5
        assert image_generator.config['WIDTH'] == 512
        assert image_generator.config['HEIGHT'] == 512

    @responses.activate
    def test_image_gen_no_response(self):
        image_generator = Automatic1111Interface()
        responses.add(responses.POST, image_generator.url,
                  json={'error': 'not found'}, status=400)
        result = image_generator.generate_image("Test image", "./tests/files", "test")
        assert result == False

    @responses.activate
    def test_image_gen(self):
        # read response from file
        with open('./tests/files/response_content.json', 'r') as file:
            response = file.read()
        responses.add(responses.POST, 'http://localhost:7860/sdapi/v1/txt2img',
                  json=json.loads(response), status=200)
        image_generator = Automatic1111Interface()
        result = image_generator.generate_image("Test image", "./tests/files", "test")
        assert result == True