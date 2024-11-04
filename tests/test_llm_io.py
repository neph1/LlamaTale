

import json
import os
from aioresponses import aioresponses
import responses

import yaml
from tale.llm.llm_io import IoUtil
from tale.player import Player, PlayerConnection
from tale.tio.iobase import IoAdapterBase


class TestLlmIo():

    def _load_config(self) -> dict:
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../llm_config.yaml")), "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    def _load_backend_config(self, backend) -> dict:
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), f"../backend_{backend}.yaml")), "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        

    def test_set_prompt_kobold_cpp(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'kobold_cpp'
        backend_config = self._load_backend_config('kobold_cpp')
        prompt = config_file['BASE_PROMPT']
        assert('### Instruction' not in prompt)
        assert('### Response' not in prompt)
        assert('USER_START' in prompt)
        assert('USER_END' not in prompt)
        request_body = json.loads(backend_config['DEFAULT_BODY'])

        io_util = IoUtil(config=config_file, backend_config=backend_config)
        result = io_util.io_adapter.set_prompt(request_body=request_body, prompt=prompt, context='context')
        if io_util.io_adapter.place_context_in_memory:
            assert(result['memory'] == '<context>context</context>')
        else:
            assert('<context>context</context>' in result['prompt'])

    def test_set_prompt_openai(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'openai'
        backend_config = self._load_backend_config('openai')
        prompt = config_file['BASE_PROMPT']
        assert('### Instruction' not in prompt)
        assert('### Response' not in prompt)
        assert('USER_START' in prompt)
        assert('USER_END' not in prompt)
        request_body = json.loads(backend_config['DEFAULT_BODY'])
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        result = io_util.io_adapter.set_prompt(request_body=request_body, prompt=prompt, context='')

    def test_set_prompt_llama_cpp(self):
        
        config_file = self._load_config()
        config_file['BACKEND'] = 'llama_cpp'
        backend_config = self._load_backend_config('llama_cpp')
        prompt = config_file['BASE_PROMPT']
        assert('### Instruction' not in prompt)
        assert('### Response' not in prompt)
        assert('USER_START' in prompt)
        assert('USER_END' not in prompt)
        request_body = json.loads(backend_config['DEFAULT_BODY'])

        io_util = IoUtil(config=config_file, backend_config=backend_config)
        result = io_util.io_adapter.set_prompt(request_body=request_body, prompt=prompt, context='context')
        assert('<context>context</context>' in result['messages'][1]['content'])
        assert(result['messages'][0]['content'] != '<context>context</context>')


    def test_password_in_header(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'kobold_cpp'

        backend_config = self._load_backend_config('kobold_cpp')
        io_util = IoUtil(config=config_file, backend_config=backend_config)

        assert not io_util.headers

        backend_config = self._load_backend_config('kobold_cpp')
        backend_config['API_PASSWORD'] = 'test_password'
        io_util = IoUtil(config=config_file, backend_config=backend_config)

        assert io_util.headers['Authorization'] == f"Bearer {backend_config['API_PASSWORD']}"

    @responses.activate
    def test_error_response(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'kobold_cpp'
        backend_config = self._load_backend_config('kobold_cpp')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'results':['']}, status=500)
        io_util = IoUtil(config=config_file, backend_config=backend_config)

        response = io_util.synchronous_request(request_body=json.loads(backend_config['DEFAULT_BODY']), prompt='test evoke', context='')
        assert(response == '')

    @responses.activate
    def test_openai_grammar(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'openai'
        backend_config = self._load_backend_config('openai')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'results':['']}, status=500)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = request_body = json.loads(backend_config['DEFAULT_BODY'])
        request_body['grammar_string'] = 'test grammar'
        response = io_util.synchronous_request(request_body=request_body, prompt='test evoke', context='')
        assert not request_body.get('grammar_string', None)
        assert request_body['response_format']

    @responses.activate
    def test_openai_local_grammar(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'openai'
        backend_config = self._load_backend_config('openai')
        backend_config['URL'] = 'http://localhost:5001'
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'results':['']}, status=500)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = request_body = json.loads(backend_config['DEFAULT_BODY'])
        request_body['grammar_string'] = 'test grammar'
        response = io_util.synchronous_request(request_body=request_body, prompt='test evoke', context='')
        assert request_body['grammar_string']
        assert not request_body.get('response_format', None)


    @responses.activate
    def test_llamacpp_grammar(self):
        backend_config = self._load_backend_config('llama_cpp')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'results':['']}, status=500)
        config_file = self._load_config()
        config_file['BACKEND'] = 'llama_cpp'
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = request_body = json.loads(backend_config['DEFAULT_BODY'])
        request_body['grammar'] = 'test grammar'
        response = io_util.synchronous_request(request_body=request_body, prompt='test evoke', context='')
        assert request_body['grammar'] == 'test grammar'

    @responses.activate
    def test_koboldcpp_grammar(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'kobold_cpp'
        backend_config = self._load_backend_config('kobold_cpp')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'results':['']}, status=500)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = request_body = json.loads(backend_config['DEFAULT_BODY'])
        request_body['grammar'] = 'test grammar'
        response = io_util.synchronous_request(request_body=request_body, prompt='test evoke', context='')
        assert request_body['grammar'] == 'test grammar'

    @responses.activate
    def test_stream_kobold_cpp(self):
        config = {'BACKEND':'kobold_cpp', 'USER_START':'', 'USER_END':''}
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), f"../backend_kobold_cpp.yaml")), "r") as stream:
            try:
                backend_config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        io_util = IoUtil(config=config, backend_config=backend_config) # type: IoUtil
        io_util.stream = True
        conn = PlayerConnection(Player('test', 'm'))
        
        responses.add(responses.POST, backend_config['URL'] + backend_config['DATA_ENDPOINT'],
                    json={'results':[{'text':'stream test'}]}, status=200)
        with aioresponses() as mocked_responses:
            # Mock the response for the specified URL
            mocked_responses.post(backend_config['URL'] + backend_config['STREAM_ENDPOINT'], 
                                 status=200,
                                 body="{'results':[{'text':'stream test'}]}")
            result = io_util.stream_request(request_body=json.loads(backend_config['DEFAULT_BODY']), prompt='test evoke', context='', io = IoAdapterBase(conn))
            assert(result == 'stream test')

    def test_stream_llama_cpp(self):
        config = {'BACKEND':'llama_cpp', 'USER_START':'', 'USER_END':''}
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), f"../backend_llama_cpp.yaml")), "r") as stream:
            try:
                backend_config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        io_util = IoUtil(config=config, backend_config=backend_config) # type: IoUtil
        io_util.stream = True
        conn = PlayerConnection(Player('test', 'm'))
        
        with aioresponses() as mocked_responses:
            # Mock the response for the specified URL
            mocked_responses.post(backend_config['URL'] + backend_config['STREAM_ENDPOINT'], 
                                 status=200,
                                 body='data: {"choices":[{"delta":{"content":"stream test"}}]}')
            result = io_util.stream_request(request_body=json.loads(backend_config['DEFAULT_BODY']), prompt='test evoke', context='', io = IoAdapterBase(conn))
            assert(result == 'stream test')
