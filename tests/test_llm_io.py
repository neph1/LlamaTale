

import json
import os

import yaml
from tale.llm import llm_config
from tale.llm.llm_io import IoUtil
from tests.supportstuff import FakeIoUtil


class TestLlmIo():


    
    llm_io = IoUtil()

    def setup(self):
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../llm_config.yaml")), "r") as stream:
            try:
                self.config_file = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.llm_io.user_start_prompt = self.config_file['USER_START']
        self.llm_io.user_end_prompt = self.config_file['USER_END']

    def _load_backend_config(self, backend):
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), f"../backend_{backend}.yaml")), "r") as stream:
            try:
                self.backend_config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        

    def test_set_prompt_kobold_cpp(self):
        self.llm_io.backend = 'kobold_cpp'
        self._load_backend_config('kobold_cpp')
        prompt = self.config_file['BASE_PROMPT']
        assert('### Instruction' not in prompt)
        assert('### Response' not in prompt)
        assert('USER_START' in prompt)
        assert('USER_END' not in prompt)
        request_body = json.loads(self.backend_config['DEFAULT_BODY'])

        result = self.llm_io._set_prompt(request_body, prompt)
        assert(self.config_file['USER_START'] in result['prompt'])
        assert(self.config_file['USER_END'] in result['prompt'])

    def test_set_prompt_openai(self):
        self.backend = 'openai'
        self._load_backend_config('openai')
        self.llm_io.backend = 'openai'
        prompt = self.config_file['BASE_PROMPT']
        assert('### Instruction' not in prompt)
        assert('### Response' not in prompt)
        assert('USER_START' in prompt)
        assert('USER_END' not in prompt)
        request_body = json.loads(self.backend_config['DEFAULT_BODY'])

        result = self.llm_io._set_prompt(request_body, prompt)
        assert(self.config_file['USER_START'] in result['messages'][1]['content'])
        assert(self.config_file['USER_END'] in result['messages'][1]['content'])

    def test_set_prompt_llama_cpp(self):
        self.backend = 'llama_cpp'
        self._load_backend_config('llama_cpp')
        self.llm_io.backend = 'llama_cpp'
        prompt = self.config_file['BASE_PROMPT']
        assert('### Instruction' not in prompt)
        assert('### Response' not in prompt)
        assert('USER_START' in prompt)
        assert('USER_END' not in prompt)
        request_body = json.loads(self.backend_config['DEFAULT_BODY'])

        result = self.llm_io._set_prompt(request_body, prompt)
        assert(self.config_file['USER_START'] in result['messages'][1]['content'])
        assert(self.config_file['USER_END'] in result['messages'][1]['content'])