import requests
import json
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from tale.errors import LlmResponseException
from tale.llm.io_adapters import KoboldCppAdapter, LlamaCppAdapter

T = TypeVar('T', bound=BaseModel)

class IoUtil():
    """ Handles connection and data retrieval from backend """

    def __init__(self, config: dict = None, backend_config: dict = None):
        if not config:
            # for tests
            return 
        self.backend = config['BACKEND']
        self.url = backend_config['URL']
        self.endpoint = backend_config['ENDPOINT']
        headers = {}
        if self.backend != 'kobold_cpp':
            headers = json.loads(backend_config['OPENAI_HEADERS'])
            headers['Authorization'] = f"Bearer {backend_config['OPENAI_API_KEY']}"
            self.headers = headers
            self.io_adapter = LlamaCppAdapter(self.url, backend_config['STREAM_ENDPOINT'], config.get('USER_START', ''), config.get('USER_END', ''), config.get('SYSTEM_START', ''), config.get('PROMPT_END', ''))
        else:
            if 'API_PASSWORD' in backend_config and backend_config['API_PASSWORD']:
                headers['Authorization'] = f"Bearer {backend_config['API_PASSWORD']}"
            self.headers = headers
            self.io_adapter = KoboldCppAdapter(self.url, backend_config['STREAM_ENDPOINT'], backend_config['DATA_ENDPOINT'], config.get('USER_START', ''), config.get('USER_END', ''), config.get('SYSTEM_START', ''), config.get('PROMPT_END', ''))

        self.stream = backend_config['STREAM']


    def synchronous_request(self, request_body: dict, prompt: str, context: str = '') -> str:
        """ Send request to backend and return the result.

        Raises LlmResponseException on non-200 so the caller sees the backend's
        error message instead of a silent empty string.
        """
        request_body = self.io_adapter.set_prompt(request_body, prompt, context)
        response = requests.post(self.url + self.endpoint, headers=self.headers, data=json.dumps(request_body))
        if response.status_code == 200:
            return self.io_adapter.parse_result(response.text)
        raise LlmResponseException(
            f"Backend returned HTTP {response.status_code}: {response.text[:500]}"
        )

    def structured_request(self, request_body: dict, prompt: str, model: Type[T], context: str = '', retries: int = 1) -> T:
        """ Send request with JSON Schema structured output and return a validated model.

        The model's JSON Schema is sent via response_format so the backend constrains
        generation to schema-valid JSON. The response is then validated by Pydantic.

        Some servers reject ``strict: true`` — if so, retries once without strict mode.
        On JSON parse/validation failure (e.g. output truncated by max_tokens), retries
        with a fresh request — truncation is transient and a re-roll often completes.
        """
        schema = model.model_json_schema()
        last_exc = None
        for strict in (True, False):
            request_body['response_format'] = {
                'type': 'json_schema',
                'json_schema': {
                    'name': model.__name__,
                    'strict': strict,
                    'schema': schema,
                },
            }
            for attempt in range(retries + 1):
                try:
                    text = self.synchronous_request(request_body, prompt=prompt, context=context)
                except LlmResponseException as exc:
                    last_exc = exc
                    if strict and 'strict' in str(exc).lower():
                        break  # strict mode rejected — fall through to non-strict
                    continue
                # Some backends return content as a list of typed parts (reasoning models);
                # normalize to a plain string before JSON validation.
                if isinstance(text, list):
                    text = ''.join(
                        part.get('text', '') for part in text
                        if isinstance(part, dict) and part.get('type') == 'text'
                    )
                if not text or not str(text).strip():
                    last_exc = LlmResponseException(
                        f"Empty response from backend for structured request ({model.__name__}). "
                        f"Output may be truncated (check max_tokens)."
                    )
                    continue
                try:
                    return model.model_validate_json(str(text))
                except ValidationError as exc:
                    last_exc = LlmResponseException(f"Failed to validate {model.__name__}: {exc}")
                    if attempt < retries:
                        print(f"Structured request for {model.__name__} failed (attempt {attempt + 1}/{retries + 1}), retrying...")
                        continue
            if not strict:
                break
        raise last_exc
    
    def asynchronous_request(self, request_body: dict, prompt: str, context: str = '') -> str:
        if self.backend != 'kobold_cpp':
            return self.synchronous_request(request_body=request_body, prompt=prompt, context=context)
        return self.stream_request(request_body, wait=True, prompt=prompt, context=context)

    def stream_request(self, request_body: dict, prompt: str, context: str = '', io = None, wait: bool = False) -> str:
        if self.io_adapter:
            request_body = self.io_adapter.set_prompt(request_body, prompt, context)
            return self.io_adapter.stream_request(self.headers, request_body, io, wait)
        # fall back if no io adapter
        return self.synchronous_request(request_body=request_body, prompt=prompt, context=context)
