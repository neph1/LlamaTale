import os
import yaml


def load_config() -> dict:
    # Load base configuration from YAML
    config_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "../../llm_config.yaml"))
    with open(config_path, "r") as stream:
        try:
            params = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            params = {}
    
    # Load prompt templates from individual files
    prompts_dir = os.path.join(os.path.dirname(__file__), "prompt_templates")
    if os.path.exists(prompts_dir):
        for filename in os.listdir(prompts_dir):
            if filename.endswith('.txt'):
                # Use filename (without .txt extension) as the key
                key = filename[:-4]
                file_path = os.path.join(prompts_dir, filename)
                with open(file_path, 'r') as f:
                    params[key] = f.read()
    
    return params

params = load_config()
