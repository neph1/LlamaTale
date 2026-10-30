"""Test-framework setup shared by all tests in this directory.

Import-time note: conftest.py is imported before any test module is collected,
so the statements below run before class-level code in test modules (e.g.
FakeDriver() instantiations) constructs LlmUtil objects.
"""

import pytest

from tale import mud_context
from tale.llm import llm_config

# Make the test suite independent of the BACKEND set in llm_config.yaml.
# All LLM-calling tests mock the kobold_cpp endpoint (http://localhost:5001)
# with the `responses` library, so any default-constructed LlmUtil() (which
# loads backend_<BACKEND>.yaml from the repo root) must resolve to kobold_cpp,
# otherwise requests go to the real configured backend and fail.
llm_config.params['BACKEND'] = 'kobold_cpp'


@pytest.fixture(autouse=True)
def _isolate_mud_context():
    """Snapshot and restore the global mud_context around each test, so test
    modules cannot leak their driver/config into other modules' tests."""
    saved = (mud_context.driver, mud_context.config, mud_context.resources)
    yield
    mud_context.driver, mud_context.config, mud_context.resources = saved
