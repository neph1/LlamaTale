import importlib
import os

import yaml

from tale.llm import llm_config


def _load_backend_config(backend: str) -> dict:
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), f"../backend_{backend}.yaml"))
    with open(path, "r") as stream:
        return yaml.safe_load(stream)


def _make_io_util(backend: str):
    from tale.llm.llm_io import IoUtil
    return IoUtil(config=llm_config.params, backend_config=_load_backend_config(backend))


class TestDockerEnvOverrides:
    """Environment variable overrides used for containerized deployments."""

    def test_backend_env_override(self, monkeypatch):
        monkeypatch.setenv("LLAMATALE_BACKEND", "llama_cpp")
        reloaded = importlib.reload(llm_config)
        try:
            assert reloaded.params['BACKEND'] == 'llama_cpp'
        finally:
            monkeypatch.delenv("LLAMATALE_BACKEND")
            importlib.reload(llm_config)

    def test_backend_default_unchanged(self, monkeypatch):
        monkeypatch.delenv("LLAMATALE_BACKEND", raising=False)
        reloaded = importlib.reload(llm_config)
        assert reloaded.params['BACKEND'] == 'kobold_cpp'

    def test_backend_url_env_override(self, monkeypatch):
        monkeypatch.setenv("KOBOLD_CPP_URL", "http://koboldcpp:5001")
        io_util = _make_io_util("kobold_cpp")
        assert io_util.url == "http://koboldcpp:5001"

    def test_backend_url_generic_env_override(self, monkeypatch):
        monkeypatch.setenv("LLAMATALE_BACKEND_URL", "http://llm-server:9000")
        io_util = _make_io_util("kobold_cpp")
        assert io_util.url == "http://llm-server:9000"

    def test_backend_url_default_unchanged(self, monkeypatch):
        monkeypatch.delenv("LLAMATALE_BACKEND_URL", raising=False)
        monkeypatch.delenv("KOBOLD_CPP_URL", raising=False)
        io_util = _make_io_util("kobold_cpp")
        assert io_util.url == "http://localhost:5001"
