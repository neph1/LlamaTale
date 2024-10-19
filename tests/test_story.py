import pytest
from tale.story import StoryContext

class TestStoryContext:

    def test_initialization(self):
        context = StoryContext(base_story="A hero's journey")
        assert context.base_story == "A hero's journey"
        assert context.current_section == ""
        assert context.past_sections == []

    def test_set_current_section(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_current_section("Chapter 1")
        assert context.current_section == "Chapter 1"
        assert context.past_sections == []

        context.set_current_section("Chapter 2")
        assert context.current_section == "Chapter 2"
        assert context.past_sections == ["Chapter 1"]

    def test_increase_progress(self):
        context = StoryContext(base_story="A hero's journey")
        result = context.increase_progress(0.01)
        assert result == False
        assert context.progress < 0.011
        context.increase_progress(0.01)
        assert context.progress < 0.021

        context.progress = 0.99999999999
        result = context.increase_progress(1)
        assert result == True
        assert context.progress > 1.0

        context.progress = 9.9999999999999999999
        context.increase_progress(1)
        assert context.progress == 10.0

    def test_to_context(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_current_section("Chapter 1")
        assert context.to_context() == "<story> Base plot: A hero's journey; Active section: Chapter 1</story>"

    def test_to_context_with_past(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_current_section("Chapter 1")
        context.set_current_section("Chapter 2")
        assert context.to_context_with_past() == "<story> Base plot: A hero's journey; Past: Chapter 1; Active section:Chapter 2; Progress: 0.0/10.0;</story>"

    def test_from_json(self):
        data = {
            "base_story": "A hero's journey",
            "current_section": "Chapter 1",
            "past_sections": ["Prologue"],
            "progress": 0.5,
            "length": 10.0,
        }
        context = StoryContext().from_json(data)
        assert context.base_story == "A hero's journey"
        assert context.current_section == "Chapter 1"
        assert context.past_sections == ["Prologue"]
        assert context.progress == 0.5
        assert context.length == 10.0

    def test_to_json(self):
        context = StoryContext(base_story="A hero's journey")
        context.set_current_section("Prologue")
        context.set_current_section("Chapter 1")
        context.set_current_section("Chapter 2")
        data = context.to_json()
        assert data == {
            "base_story": "A hero's journey",
            "current_section": "Chapter 2",
            "past_sections": ["Prologue", "Chapter 1"],
            "progress": 0.0,
            "length": 10.0,
            "speed": 1.0
        }