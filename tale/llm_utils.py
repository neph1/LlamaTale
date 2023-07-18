import json
import yaml
import os

class LlmUtil():
    def __init__(self):
        with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "llm_config.yaml")), "r") as stream:
            try:
                config_file = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        self.url = config_file['URL'] + config_file['ENDPOINT']
        self.default_body = json.loads(config_file['DEFAULT_BODY'])
        
