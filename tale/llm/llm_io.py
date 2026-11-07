import collections
import os
import requests
import json
from typing import Any, Dict, List, Literal, Sequence, Type, TypeVar, Union, get_args, get_origin
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
        # Allow the backend server URL to be overridden via environment variable,
        # so containers can point at a backend on another host without editing the YAML.
        url_override = os.environ.get(f"{self.backend.upper()}_URL") or os.environ.get("LLAMATALE_BACKEND_URL")
        self.url = url_override or backend_config['URL']
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


def _default_for_annotation(annotation: Any) -> Any:
    """A minimal canned value for a required pydantic field of the given type."""
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        return _default_for_annotation(args[0]) if args else None
    if origin is Literal:
        args = get_args(annotation)
        return args[0] if args else None
    if origin in (list, dict):
        return origin()
    if annotation is str:
        return "ok"
    if annotation is bool:
        return False
    if annotation is int:
        return 0
    if annotation is float:
        return 0.0
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _empty_model_data(annotation)
    return None


def _empty_model_data(model: Type[BaseModel]) -> Dict[str, Any]:
    """Values for all required fields of the model; fields with defaults are left to pydantic."""
    return {name: _default_for_annotation(field.annotation)
            for name, field in model.model_fields.items() if field.is_required()}


class DummyIoUtil(IoUtil):
    """Dummy LLM backend that answers with canned responses instead of contacting a real server.

    Used for smoke tests and offline runs (set BACKEND: dummy in llm_config.yaml, or let
    tale.smoketest select it). Plain requests get the next canned response from `responses`
    (or `default_response` when the queue is empty). Structured requests validate the canned
    response against the requested model; if it doesn't fit, a minimal schema-valid instance
    is constructed from the model's field defaults.
    """

    DEFAULT_RESPONSE = "The story continues quietly."

    def __init__(self, responses: Sequence[str] = (), default_response: str = None):
        super().__init__()   # no config: this backend never talks to a server
        self.backend = 'dummy'
        self.stream = False
        self.io_adapter = None
        self.responses = collections.deque(responses)  # type: collections.deque
        self.default_response = default_response if default_response is not None else self.DEFAULT_RESPONSE
        self.requests: List[str] = []   # prompts seen, for debugging and assertions

    def _next_response(self, prompt: str = None) -> str:
        self.requests.append(prompt or '')
        if self.responses:
            return self.responses.popleft()
        return self.default_response

    def synchronous_request(self, request_body: dict, prompt: str = None, context: str = '') -> str:
        return self._next_response(prompt)

    def asynchronous_request(self, request_body: dict, prompt: str = None, context: str = '') -> str:
        return self._next_response(prompt)

    def stream_request(self, request_body: dict, prompt: str = None, context: str = '', io=None, wait: bool = False) -> str:
        return self._next_response(prompt)

    def structured_request(self, request_body: dict, prompt: str = None, model: Type[T] = None, context: str = '', retries: int = 1) -> T:
        text = self._next_response(prompt)
        try:
            return model.model_validate_json(text)
        except ValidationError:
            try:
                return model.model_validate(_empty_model_data(model))
            except ValidationError as exc:
                raise LlmResponseException(
                    f"Dummy backend has no valid canned answer for {model.__name__}: {text!r} ({exc})")
