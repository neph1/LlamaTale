

import datetime
import pytest
from tale import util, mud_context
from tale.driver_if import IFDriver
from tale.llm.dynamic_story import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.player import PlayerConnection
from tale.story import StoryConfig
from tale.story_builder import StoryBuilder, StoryInfo
from tests.supportstuff import FakeIoUtil


class TestStoryBuilder():
    story_builder = StoryBuilder(PlayerConnection())

    def test_build(self):
        
        builder = self.story_builder.build()

        input, prompt = next(builder)

        assert(input == "input")
        assert(prompt == "What genre would you like your story to be? Ie, 'A post apocalyptic scifi survival adventure', or 'Cozy social simulation with deep characters'")

        input, prompt = builder.send("A post apocalyptic scifi survival adventure")

        assert(input == "input")
        assert(prompt == "Describe what the world is like. Use one to two paragraphs to outline the world and what it's like.")

        input, prompt = builder.send("The world is a post apocalyptic world where the machines have taken over.")

        assert(input == "input")
        assert(prompt == "How safe is the world? 5 is a happy place, -5 is nightmare mode.", self.story_builder.validate_mood)

        input, prompt = builder.send(5)

        assert(input == "input")
        assert(prompt == "Where does the story start? Describe the starting location.")

        assert self.story_builder.story_info.world_mood == 5
        assert self.story_builder.story_info.type == "A post apocalyptic scifi survival adventure"
        assert self.story_builder.story_info.world_info == "The world is a post apocalyptic world where the machines have taken over."

        # story_info = builder.
        # assert(isinstance(story_info, StoryInfo))

    def test_validate_mood(self):
        assert(self.story_builder.validate_mood(5) == 5)

        assert(self.story_builder.validate_mood(-5) == -5)

        assert(self.story_builder.validate_mood("0") == 0)

        assert(self.story_builder.validate_mood(None) == 0)

        with pytest.raises(ValueError):
            self.story_builder.validate_mood(10)


        with pytest.raises(ValueError):
            self.story_builder.validate_mood("X")

    def test_apply_to_story(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        driver.moneyfmt = util.MoneyFormatterFantasy()
        builder = StoryBuilder(PlayerConnection())

        builder.story_info.name = "A Tale of Anything"
        builder.story_info.type = "a cozy farming simulator set in a fantasy world"
        builder.story_info.world_info = "a mix between alice in wonderland and the wizard of oz with a dark element"
        builder.story_info.world_mood = 3
        builder.story_info.start_location = "on a small road outside a village"

        responses = ['In the peaceful land of Whimsy, where the sun always shines bright and the creatures are forever young, a darkness has begun to stir beneath the surface. A great evil, born from the twisted imagination of the Mad Hatter, threatens to consume the entire realm. This malevolent force seeks to plunge Whimsy into eternal night, and all who oppose it must band together if they hope to save their home from destruction. The players\' village is the first to fall under attack, forcing them to embark on a perilous journey across this magical landscape to rally allies for the impending war against the shadowy foe. Along the way, they discover hidden secrets about the nature of their world and their own roles within its grand narrative, ultimately deciding the fate of an enchanted civilization hanging precariously upon their shoulders.',
            '{"items":[{"name":"Enchanted Petals", "type":"Health", "value": 20, "description": "A handful of enchanted petals that can be used to heal wounds and cure ailments."}]}',
            '{"creatures": [   {   "name": "Whimsy Woozle",   "description": "A gentle, ethereal creature with a penchant for gardening and poetry. They tend to the area\'s lush fields and forests, filling the air with sweet melodies and the scent of blooming wildflowers. They are friendly and welcoming to all visitors.",   "level": 1   },   {   "name": "Lunar Lopster",   "description": "A mysterious crustacean with an affinity for the moon\'s gentle light. They roam the area at night, their glowing shells lighting the way through the darkness. They are neutral towards visitors, but may offer cryptic advice or guidance to those who seek it.",   "level": 2   },   {   "name": "Shadow Stag",   "description": "A sleek and elusive creature with a mischievous grin. They roam the area\'s forests, their dark forms blending into the shadows. They are hostile towards intruders, and will not hesitate to attack those who threaten their home.",   "level": 3   },   {   "name": "Moonflower",   "description": "A rare and beautiful flower that blooms only under the light of the full moon. They can be found in the area\'s forests, and are said to have powerful healing properties. They are very friendly towards visitors, and will offer their petals to those who show kindness and respect.",   "level": 4   },   {   "name": "Moonstone",   "description": "A rare and valuable mineral that can be found in the area\'s mountains. It glows with a soft, ethereal light, and is said to have powerful magical properties. It is highly sought after by collectors, and can be found in both the earth and the water.",   "level": 5   }]}',
            '{   "name": "Moonlit Meadows",   "description": "A serene and mystical area nestled between two great mountains, where the moon\'s gentle light illuminates the lush fields and forests. The air is filled with the sweet scent of blooming wildflowers, and the gentle chirping of nocturnal creatures can be heard in the distance. The area is home to a diverse array of magical creatures, including the Whimsy Woozle, the Lunar Lopster, and the Shadow Stag."}',
            '{"name": "Greenhaven", "exits": [{"direction": "south", "name": "Moonflower Meadow", "description": "A lush field of wildflowers, home to the elusive Moonflower. The air is filled with the sweet scent of blooming blossoms, and the gentle chirping of nocturnal creatures can be heard in the distance."}, {"direction": "north", "name": "Shadowy Woods", "description": "A dark and foreboding forest, home to the Shadow Stag. The trees tower above, casting long shadows that seem to move and twist in the flickering moonlight."}, {"direction": "west", "name": "Whimsy Wastes", "description": "A barren and desolate landscape, filled with the remnants of a long-forgotten civilization. The sandy dunes shift and swirl in the wind, and the only sound is the distant howling of unseen beasts."}], "items": ["Enchanted Petals"], "npcs": [{"name": "Rosewood Fairy", "sentiment": "friendly", "race": "Fae", "gender": "female", "level": 5, "description": "A delicate creature with wings as soft as rose petals, offering quests and guidance."}]}',
            ]

        story = DynamicStory()

        llm_util = LlmUtil(io_util=FakeIoUtil(response=responses))
        llm_util.set_story(story)
        
        start_location = builder.apply_to_story(story, llm_util)

        assert(start_location.name == "Greenhaven")
        assert(start_location.exits["moonflower meadow"])
        assert(start_location.exits["shadowy woods"])
        assert(len(story._catalogue._creatures) == 5)
        assert(story._catalogue._creatures[0]["name"] == "Whimsy Woozle")
        assert(story._catalogue._creatures[1]["name"] == "Lunar Lopster")
        creature = story._catalogue._creatures[2]
        assert(creature["name"] == "Shadow Stag")
        assert(creature["level"] == 3)
        assert(len(story.catalogue._items) == 1)
        assert(story.catalogue._items[0]["name"] == "Enchanted Petals")

        assert(story.config.name == "A Tale of Anything")
        assert(story.config.type == "a cozy farming simulator set in a fantasy world")
        assert(story.config.world_info == "a mix between alice in wonderland and the wizard of oz with a dark element")
        assert(story.config.world_mood == 3)
        assert(story.config.startlocation_player == "Moonlit Meadows.Greenhaven")
        
        quest = None
        assert(start_location.livings)
        for npc in start_location.livings:
            if npc.quest:
                quest = npc.quest
                break
        assert(quest)

        