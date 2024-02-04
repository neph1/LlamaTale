import json
import responses
from tale.image_gen.automatic1111 import Automatic1111
from tale.llm.LivingNpc import LivingNpc
from tale.llm.llm_utils import LlmUtil
from tale.thread_utils import do_in_background
from tests.supportstuff import FakeIoUtil


class TestAutomatic():

    def setup_method(self):
        with open('./tests/files/response_content.json', 'r') as file:
            response = file.read()
        responses.add(responses.POST, 'http://127.0.0.1:7860/sdapi/v1/txt2img',
                  json=json.loads(response), status=200)
        self.image_generator = Automatic1111()

    def test_image_gen_config(self):
        image_generator = Automatic1111()
        assert image_generator.config['ALWAYS_PROMPT'] == 'closeup'
        assert image_generator.config['NEGATIVE_PROMPT'] == 'text, watermark, logo'
        assert image_generator.config['SEED'] == -1
        assert image_generator.config['SAMPLER'] == 'Euler'
        assert image_generator.config['STEPS'] == 30
        assert image_generator.config['CFG_SCALE'] == 5
        assert image_generator.config['WIDTH'] == 512
        assert image_generator.config['HEIGHT'] == 512

    @responses.activate
    def test_image_gen(self):
        result = self.image_generator.generate_image("Test image", "./tests/files", "test")
        assert result == True

    @responses.activate
    def test_generate_avatar(self):
        llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil
        llm_util._init_image_gen("Automatic1111")
        # Not copying file for now, due to test folder set up
        result = llm_util.generate_image(description='test prompt', name='test name', save_path='./tests/files', copy_file=False)
        assert result == True

    @responses.activate
    def test_generate_avatar_npc(self):
        llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil
        llm_util._init_image_gen("Automatic1111")
        npc = LivingNpc('test', 'f', age=30)
        assert npc.avatar == None
        result = llm_util.generate_image(description='test prompt', name='test name', save_path='./tests/files', copy_file=False, target=npc)
        assert npc.avatar == 'test_name.jpg'
        assert result == True

    def test_generate_avatar_no_image_gen(self):
        llm_util = LlmUtil(FakeIoUtil())
        result = llm_util.generate_image(description='test prompt', name='test name', save_path='./tests/files', copy_file=False)
        assert result == False

    @responses.activate
    def test_generate_in_background(self):
        lambda_task = lambda result_event: result_event.set() if self.image_generator.generate_image("Test image", "./tests/files", "test") else result_event.clear()
        result = do_in_background(lambda_task)

        assert result

    @responses.activate
    def test_generate_avatar_npc_background(self):
        llm_util = LlmUtil(FakeIoUtil()) # type: LlmUtil
        llm_util._init_image_gen("Automatic1111")
        llm_util._image_gen.generate_in_background = True
        npc = LivingNpc('test', 'f', age=30)
        assert npc.avatar == None
        result = llm_util.generate_image(description='test prompt', name='test name', save_path='./tests/files', copy_file=False, target=npc)
        assert npc.avatar == 'test_name.jpg'
        assert result == True

class TestAutomaticError():

    @responses.activate
    def test_image_gen_no_response(self):
        image_generator = Automatic1111()
        responses.add(responses.POST, image_generator.url,
                  json={'error': 'not found'}, status=400)
        result = image_generator.generate_image("Test image", "./tests/files", "test")
        assert result == False


    @responses.activate
    def test_generate_in_background_no_response(self):
        image_generator = Automatic1111()
        responses.add(responses.POST, image_generator.url,
                  json={'error': 'not found'}, status=400)
        
        lambda_task = lambda result_event: result_event.set() if image_generator.generate_image("Test image", "./tests/files", "test") else result_event.clear()

        result = do_in_background(lambda_task)

        assert result == False