

import pytest
from tale.player import PlayerConnection
from tale.story import StoryConfig
from tale.story_builder import StoryBuilder, StoryInfo


class TestStoryBuilder():
    conn = PlayerConnection()
    story_builder = StoryBuilder(conn)

    def test_build(self):
        
        builder = self.story_builder.build()

        input, prompt = next(builder)

        assert(input, "input")
        assert(prompt, "What genre would you like your story to be? Ie, 'A post apocalyptic scifi survival adventure', or 'Cozy social simulation with deep characters'")

        input, prompt = builder.send("A post apocalyptic scifi survival adventure")

        assert(input, "input")
        assert(prompt, "Describe what the world is like. Use one to two paragraphs to outline the world and what it's like.")

        input, prompt = builder.send("The world is a post apocalyptic world where the machines have taken over.")

        assert(input, "input")
        assert(prompt, "How safe is the world? 5 is a happy place, -5 is nightmare mode.")

        input, prompt = builder.send(5)

        assert(input, "input")
        assert(prompt, "Where does the story start? Describe the starting location.")

        # story_info = builder.
        # assert(isinstance(story_info, StoryInfo))

    def test_validate_mood(self):
        value = self.story_builder.validate_mood(5)
        assert(value, 5)

        value = self.story_builder.validate_mood(-5)
        assert(value, -5)

        with pytest.raises(ValueError):
            self.story_builder.validate_mood(10)


        with pytest.raises(ValueError):
            self.story_builder.validate_mood("X")
        