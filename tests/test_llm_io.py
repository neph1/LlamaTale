import json
import os
from aioresponses import aioresponses
import responses

import yaml
from tale.errors import LlmResponseException
from tale.llm import llm_config
from tale.llm.llm_io import IoUtil
from tale.llm.schemas import FollowSchema
from tale.player import Player, PlayerConnection
from tale.tio.iobase import IoAdapterBase


class TestLlmIo():

    def _load_config(self) -> dict:
        return llm_config.load_config()

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
    def test_structured_request_sets_response_format(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'llama_cpp'
        backend_config = self._load_backend_config('llama_cpp')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'choices': [{'message': {'content': '{"response": "yes", "reason": "because"}'}}]}, status=200)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = json.loads(backend_config['DEFAULT_BODY'])
        model = io_util.structured_request(request_body=request_body, prompt='test', model=FollowSchema, context='')
        assert model.response == 'yes'
        assert model.reason == 'because'
        assert 'response_format' in request_body
        assert request_body['response_format']['type'] == 'json_schema'
        assert request_body['response_format']['json_schema']['name'] == 'FollowSchema'

    @responses.activate
    def test_structured_request_koboldcpp(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'kobold_cpp'
        backend_config = self._load_backend_config('kobold_cpp')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'results': [{'text': '{"response": "no", "reason": "not interested"}'}]}, status=200)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = json.loads(backend_config['DEFAULT_BODY'])
        model = io_util.structured_request(request_body=request_body, prompt='test', model=FollowSchema, context='')
        assert model.response == 'no'
        assert model.reason == 'not interested'
        assert 'response_format' in request_body

    @responses.activate
    def test_structured_request_multi_part_content(self):
        """Reasoning models (DeepSeek, QwQ) return content as a list of typed parts."""
        config_file = self._load_config()
        config_file['BACKEND'] = 'llama_cpp'
        backend_config = self._load_backend_config('llama_cpp')
        multi_part = [
            {'type': 'thinking', 'thinking': 'Let me think about this...'},
            {'type': 'text', 'text': '{"response": "yes", "reason": "because"}'},
        ]
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'choices': [{'message': {'content': multi_part}}]}, status=200)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = json.loads(backend_config['DEFAULT_BODY'])
        model = io_util.structured_request(request_body=request_body, prompt='test', model=FollowSchema, context='')
        assert model.response == 'yes'
        assert model.reason == 'because'

    @responses.activate
    def test_parse_result_multi_part_content(self):
        """LlamaCppAdapter.parse_result should concatenate text parts from multi-part content."""
        from tale.llm.io_adapters import LlamaCppAdapter
        adapter = LlamaCppAdapter('http://localhost:8080', '/v1/chat/completions', '', '', '', '')
        multi_part = [
            {'type': 'thinking', 'thinking': 'internal reasoning'},
            {'type': 'text', 'text': 'Hello '},
            {'type': 'text', 'text': 'world'},
        ]
        result = json.dumps({'choices': [{'message': {'content': multi_part}}]})
        assert adapter.parse_result(result) == 'Hello world'

    @responses.activate
    def test_structured_request_empty_content_with_http_error(self):
        """Non-200 from backend should print error and structured_request should raise."""
        config_file = self._load_config()
        config_file['BACKEND'] = 'llama_cpp'
        backend_config = self._load_backend_config('llama_cpp')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'error': {'message': 'response_format json_schema not supported by this model'}}, status=400)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = json.loads(backend_config['DEFAULT_BODY'])
        try:
            io_util.structured_request(request_body=request_body, prompt='test', model=FollowSchema, context='')
            assert False, "Expected LlmResponseException"
        except LlmResponseException as exc:
            assert 'Empty response' in str(exc)
            assert 'response_format' in str(exc)

    @responses.activate
    def test_parse_result_null_content(self):
        """Reasoning models may return content: null when truncated."""
        from tale.llm.io_adapters import LlamaCppAdapter
        adapter = LlamaCppAdapter('http://localhost:8080', '/v1/chat/completions', '', '', '', '')
        result = json.dumps({'choices': [{'message': {'content': None, 'reasoning_content': 'long thinking...'}}]})
        assert adapter.parse_result(result) == ''

    @responses.activate
    def test_parse_result_only_thinking_parts(self):
        """Multi-part content with only thinking parts returns empty string."""
        from tale.llm.io_adapters import LlamaCppAdapter
        adapter = LlamaCppAdapter('http://localhost:8080', '/v1/chat/completions', '', '', '', '')
        result = json.dumps({'choices': [{'message': {'content': [
            {'type': 'thinking', 'thinking': 'only reasoning, no text output'}
        ]}}]})
        assert adapter.parse_result(result) == ''

    @responses.activate
    def test_parse_result_string_content(self):
        """LlamaCppAdapter.parse_result should pass through plain string content."""
        from tale.llm.io_adapters import LlamaCppAdapter
        adapter = LlamaCppAdapter('http://localhost:8080', '/v1/chat/completions', '', '', '', '')
        result = json.dumps({'choices': [{'message': {'content': 'plain text'}}]})
        assert adapter.parse_result(result) == 'plain text'

    @responses.activate
    def test_structured_request_validation_error(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'llama_cpp'
        backend_config = self._load_backend_config('llama_cpp')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'choices': [{'message': {'content': 'not valid json'}}]}, status=200)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = json.loads(backend_config['DEFAULT_BODY'])
        try:
            io_util.structured_request(request_body=request_body, prompt='test', model=FollowSchema, context='')
            assert False, "Expected LlmResponseException"
        except LlmResponseException:
            pass

    @responses.activate
    def test_structured_request_empty_response(self):
        config_file = self._load_config()
        config_file['BACKEND'] = 'llama_cpp'
        backend_config = self._load_backend_config('llama_cpp')
        responses.add(responses.POST, backend_config['URL'] + backend_config['ENDPOINT'],
                    json={'choices': [{'message': {'content': ''}}]}, status=200)
        io_util = IoUtil(config=config_file, backend_config=backend_config)
        request_body = json.loads(backend_config['DEFAULT_BODY'])
        try:
            io_util.structured_request(request_body=request_body, prompt='test', model=FollowSchema, context='')
            assert False, "Expected LlmResponseException"
        except LlmResponseException:
            pass

    @responses.activate
    def test_stream_kobold_cpp(self):
        config = {'BACKEND':'kobold_cpp', 'USER_START':'', 'USER_END':''}
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), f"../backend_kobold_cpp.yaml")), "r") as stream:
            try:
                backend_config = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        io_util = IoUtil(config=config, backend_config=backend_config)
        io_util.stream = True
        conn = PlayerConnection(Player('test', 'm'))

        responses.add(responses.POST, backend_config['URL'] + backend_config['DATA_ENDPOINT'],
                    json={'results':[{'text':'stream test'}]}, status=200)
        with aioresponses() as mocked_responses:
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
        io_util = IoUtil(config=config, backend_config=backend_config)
        io_util.stream = True
        conn = PlayerConnection(Player('test', 'm'))

        with aioresponses() as mocked_responses:
            mocked_responses.post(backend_config['URL'] + backend_config['STREAM_ENDPOINT'],
                                 status=200,
                                 body='data: {"choices":[{"delta":{"content":"stream test"}}]}')
            result = io_util.stream_request(request_body=json.loads(backend_config['DEFAULT_BODY']), prompt='test evoke', context='', io = IoAdapterBase(conn))
            assert(result == 'stream test')
