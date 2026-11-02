from tale.llm import llm_config

# The tests mock the kobold_cpp backend, so don't let a locally configured
# BACKEND in llm_config.yaml (e.g. ollama) send requests to a real server.
llm_config.params['BACKEND'] = 'kobold_cpp'
