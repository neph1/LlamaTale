import os
from tale.llm import llm_config


class TestLlmConfig:
    """Test LlmConfig loading from YAML and individual prompt files"""

    def test_config_keys_loaded(self):
        """Test that configuration keys are loaded from YAML"""
        assert 'WORD_LIMIT' in llm_config.params
        assert 'SHORT_WORD_LIMIT' in llm_config.params
        assert 'BACKEND' in llm_config.params
        assert 'MEMORY_SIZE' in llm_config.params
        assert 'UNLIMITED_REACTS' in llm_config.params
        assert 'ACTION_LIST' in llm_config.params
        assert 'ITEM_TYPES' in llm_config.params
        
    def test_config_values(self):
        """Test that configuration values are correct"""
        assert llm_config.params['WORD_LIMIT'] == 200
        assert llm_config.params['SHORT_WORD_LIMIT'] == 25
        assert llm_config.params['BACKEND'] == 'kobold_cpp'
        assert llm_config.params['MEMORY_SIZE'] == 512
        
    def test_prompt_templates_loaded(self):
        """Test that prompt templates are loaded from individual files"""
        # Check a few key prompts
        assert 'PRE_PROMPT' in llm_config.params
        assert 'BASE_PROMPT' in llm_config.params
        assert 'DIALOGUE_PROMPT' in llm_config.params
        assert 'COMBAT_PROMPT' in llm_config.params
        assert 'CREATE_CHARACTER_PROMPT' in llm_config.params
        
    def test_prompt_template_values(self):
        """Test that prompt template values are strings"""
        assert isinstance(llm_config.params['PRE_PROMPT'], str)
        assert len(llm_config.params['PRE_PROMPT']) > 0
        assert 'creative game keeper' in llm_config.params['PRE_PROMPT']
        
    def test_all_template_keys(self):
        """Test that all expected template keys are present"""
        template_keys = [
            'DIALOGUE_TEMPLATE', 'ACTION_TEMPLATE', 'ITEM_TEMPLATE',
            'CREATURE_TEMPLATE', 'EXIT_TEMPLATE', 'NPC_TEMPLATE',
            'LOCATION_TEMPLATE', 'ZONE_TEMPLATE', 'DUNGEON_LOCATION_TEMPLATE',
            'CHARACTER_TEMPLATE', 'FOLLOW_TEMPLATE'
        ]
        for key in template_keys:
            assert key in llm_config.params, f"Missing template key: {key}"
            
    def test_all_prompt_keys(self):
        """Test that all expected prompt keys are present"""
        prompt_keys = [
            'PRE_PROMPT', 'BASE_PROMPT', 'DIALOGUE_PROMPT', 'COMBAT_PROMPT',
            'PRE_JSON_PROMPT', 'CREATE_CHARACTER_PROMPT', 'CREATE_LOCATION_PROMPT',
            'CREATE_ZONE_PROMPT', 'CREATE_DUNGEON_LOCATIONS', 'ITEMS_PROMPT',
            'SPAWN_PROMPT', 'IDLE_ACTION_PROMPT', 'TRAVEL_PROMPT',
            'REACTION_PROMPT', 'STORY_BACKGROUND_PROMPT', 'START_LOCATION_PROMPT',
            'STORY_PLOT_PROMPT', 'WORLD_ITEMS', 'WORLD_ITEM_SINGLE',
            'WORLD_CREATURES', 'WORLD_CREATURE_SINGLE', 'GOAL_PROMPT',
            'JSON_GRAMMAR', 'PLAYER_ENTER_PROMPT', 'QUEST_PROMPT',
            'NOTE_QUEST_PROMPT', 'NOTE_LORE_PROMPT', 'ACTION_PROMPT',
            'REQUEST_FOLLOW_PROMPT', 'DAY_CYCLE_EVENT_PROMPT',
            'NARRATIVE_EVENT_PROMPT', 'RANDOM_SPAWN_PROMPT', 'ADVANCE_STORY_PROMPT'
        ]
        for key in prompt_keys:
            assert key in llm_config.params, f"Missing prompt key: {key}"
            
    def test_prompt_files_exist(self):
        """Test that prompt template files exist in the expected directory"""
        prompts_dir = os.path.join(os.path.dirname(llm_config.__file__), "prompt_templates")
        assert os.path.exists(prompts_dir), "prompt_templates directory does not exist"
        
        # Check that there are .txt files in the directory
        txt_files = [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
        assert len(txt_files) > 0, "No .txt files found in prompt_templates directory"
