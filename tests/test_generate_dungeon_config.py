"""
Tests for dungeon config generation.

Note: These are basic tests that verify the structure and interfaces.
Full integration tests require the LLM dependencies (aiohttp, etc).
"""

import json
from tale.dungeon.dungeon_config import DungeonConfig


class TestDungeonConfigGeneration:
    """Test dungeon config generation components."""

    def test_dungeon_config_prompt_template_exists(self):
        """Test that the prompt templates exist and can be loaded."""
        from tale.llm import llm_config
        
        # Verify the prompt templates are loaded
        assert 'CREATE_DUNGEON_CONFIG_PROMPT' in llm_config.params
        assert 'DUNGEON_CONFIG_TEMPLATE' in llm_config.params
        
        # Verify template structure
        template = llm_config.params['DUNGEON_CONFIG_TEMPLATE']
        assert 'name' in template
        assert 'description' in template
        assert 'races' in template
        assert 'items' in template
        assert 'max_depth' in template
        
    def test_dungeon_config_template_format(self):
        """Test that the dungeon config template has the correct structure."""
        from tale.llm import llm_config
        
        template = llm_config.params['DUNGEON_CONFIG_TEMPLATE']
        
        # Parse the template as JSON to verify it's valid
        try:
            # The template uses (int) placeholders, so we replace them for parsing
            test_template = template.replace('(int)', '1')
            test_data = json.loads(test_template)
            
            # Verify expected keys exist
            assert 'name' in test_data
            assert 'description' in test_data
            assert 'races' in test_data
            assert 'items' in test_data
            assert 'max_depth' in test_data
        except json.JSONDecodeError:
            assert False, "DUNGEON_CONFIG_TEMPLATE is not valid JSON structure"
    
    def test_dungeon_config_prompt_has_context_placeholder(self):
        """Test that the prompt has context placeholder."""
        from tale.llm import llm_config
        
        prompt = llm_config.params['CREATE_DUNGEON_CONFIG_PROMPT']
        assert '{context}' in prompt
        assert '{zone_info}' in prompt
        assert '{dungeon_config_template}' in prompt


