import requests
import json
from tale.errors import LlmResponseException
from tale.llm.io_adapters import KoboldCppAdapter, LlamaCppAdapter

class IoUtil():
    """ Handles connection and data retrieval from backend """

    def __init__(self, config: dict = None, backend_config: dict = None):
        if not config:
            # for tests
            return 
        self.backend = config['BACKEND']
        self.url = backend_config['URL']
        self.endpoint = backend_config['ENDPOINT']
        if self.backend != 'kobold_cpp':
            headers = json.loads(backend_config['OPENAI_HEADERS'])
            headers['Authorization'] = f"Bearer {backend_config['OPENAI_API_KEY']}"
            self.openai_json_format = json.loads(backend_config['OPENAI_JSON_FORMAT'])
            self.headers = headers
            self.io_adapter = LlamaCppAdapter(self.url, backend_config['STREAM_ENDPOINT'], config['USER_START'], config['USER_END'])
        else:
            self.io_adapter = KoboldCppAdapter(self.url, backend_config['STREAM_ENDPOINT'], backend_config['DATA_ENDPOINT'], config['USER_START'], config['USER_END'])
            self.headers = {}

        self.stream = backend_config['STREAM']


    def synchronous_request(self, request_body: dict, prompt: str, context: str = '') -> str:
        """ Send request to backend and return the result """
        if request_body.get('grammar', None) and 'openai' in self.url:
            # TODO: temp fix for openai
            request_body.pop('grammar')
            request_body['response_format'] = self.openai_json_format
        request_body = self.io_adapter.set_prompt(request_body, prompt, context)
        response = requests.post(self.url + self.endpoint, headers=self.headers, data=json.dumps(request_body))
        if response.status_code == 200:
            return self.io_adapter.parse_result(response.text)
        return ''
    
    def asynchronous_request(self, request_body: dict, prompt: str, context: str = '') -> str:
        if self.backend != 'kobold_cpp':
            return self.synchronous_request(request_body=request_body, prompt=prompt, context=context)
        return self.stream_request(request_body, wait=True, prompt=prompt, context=context)

    def stream_request(self, request_body: dict, prompt: str, context: str = '', io = None, wait: bool = False) -> str:
        print("context 1 " + context)
        if self.io_adapter:
            request_body = self.io_adapter.set_prompt(request_body, prompt, context)
            return self.io_adapter.stream_request(request_body, io, wait)
        # fall back if no io adapter
        return self.synchronous_request(request_body=request_body, prompt=prompt, context=context)

