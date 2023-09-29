import os
import yaml


def load_config() -> dict:
    with open(os.path.realpath(os.path.join(os.path.dirname(__file__), "../../llm_config.yaml")), "r") as stream:
        try:
            params = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
        return params

params = load_config()