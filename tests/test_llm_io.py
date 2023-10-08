

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

    def test_set_prompt_kobold_cpp(self):
        self.llm_io.backend = 'kobold_cpp'
        prompt = self.config_file['BASE_PROMPT']
        assert('### Instruction' not in prompt)
        assert('### Response' not in prompt)
        assert('USER_START' in prompt)
        assert('USER_END' not in prompt)
        request_body = json.loads(self.config_file['DEFAULT_BODY'])

        result = self.llm_io._set_prompt(request_body, prompt)
        assert('### Instruction' in result['prompt'])
        assert('### Response' in result['prompt'])

    def test_set_prompt_openai(self):
        self.llm_io.backend = 'openai'
        prompt = self.config_file['BASE_PROMPT']
        assert('### Instruction' not in prompt)
        assert('### Response' not in prompt)
        assert('USER_START' in prompt)
        assert('USER_END' not in prompt)
        request_body = json.loads(self.config_file['OPENAI_BODY'])

        result = self.llm_io._set_prompt(request_body, prompt)
        assert('### Instruction' in result['messages'][1]['content'])
        assert('### Response' in result['messages'][1]['content'])