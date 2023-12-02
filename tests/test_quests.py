import tale
from tale.base import Item, ParseResult
from tale.driver import Driver
from tale.llm.LivingNpc import LivingNpc
from tale.llm.llm_ext import DynamicStory
from tale.llm.llm_utils import LlmUtil
from tale.quest import Quest, QuestStatus, QuestType
from tale.story import StoryConfig
from tests.supportstuff import FakeDriver, FakeIoUtil


class TestGiveQuest():

    testNpc = LivingNpc("TestNpc", "m", age=20)
    testNpc2 = LivingNpc("TestNpc2", "m", age=20)

    
    tale.mud_context.config = StoryConfig()
    llm_util = LlmUtil(FakeIoUtil(response='{"response": "ok", "give":"", "sentiment":"pleased"}'))
    llm_util.set_story(DynamicStory())
    

    def test_give_quest(self):
        quest = Quest(name="TestQuest", reason="out of bowling balls", reward=100, giver=self.testNpc.name, type=QuestType.GIVE, target="bowling ball")
        self.testNpc.quest = quest
        tale.mud_context.driver = FakeDriver()
        tale.mud_context.driver.llm_util = self.llm_util
        item = Item("bowling ball", "bowling ball")
        self.testNpc2.init_inventory([item])
        parse_result = ParseResult(verb="give", unparsed="bowling ball to TestNpc")
        self.testNpc.notify_action(parsed=parse_result, actor=self.testNpc2)

        assert(quest.status == QuestStatus.COMPLETED)
        assert(self.testNpc2.search_item("bowling ball") == None)
        assert(self.testNpc.quest == None)

    def test_give_quest_alt_command(self):
        quest = Quest(name="TestQuest", reason="out of bowling balls", reward=100, giver=self.testNpc.name, type=QuestType.GIVE, target="bowling ball")
        self.testNpc.quest = quest

        item = Item("bowling ball", "bowling ball")
        self.testNpc2.init_inventory([item])
        parse_result = ParseResult(verb="give", unparsed="TestNpc bowling ball")
        self.testNpc.notify_action(parsed=parse_result, actor=self.testNpc2)

        assert(quest.status == QuestStatus.COMPLETED)
        assert(self.testNpc2.search_item("bowling ball") == None)
        assert(self.testNpc.quest == None)

    def test_give_quest_wrong_item(self):
        quest = Quest(name="TestQuest", reason="out of bowling balls", reward=100, giver=self.testNpc.name, type=QuestType.GIVE, target="bowling ball")
        quest.set_status(QuestStatus.NOT_COMPLETED)
        self.testNpc.quest = quest

        item = Item("gummy bear", "gummy bear")
        self.testNpc2.init_inventory([item])
        parse_result = ParseResult(verb="give", unparsed="gummy bear to TestNpc3")
        self.testNpc.notify_action(parsed=parse_result, actor=self.testNpc2)

        assert(quest.status == QuestStatus.NOT_COMPLETED)
        assert(self.testNpc2.search_item("gummy bear") == None) # npc will still accept the item
        assert(self.testNpc.search_item("gummy bear") != None)
        assert(self.testNpc.quest == quest)

    def test_give_quest_not_started(self):
        """ Giving a quest item will finish the quest, even if it is not started."""
        quest = Quest(name="TestQuest", reason="out of bowling balls", reward=100, giver=self.testNpc.name, type=QuestType.GIVE, target="bowling ball")
        self.testNpc.quest = quest

        item = Item("bowling ball", "bowling ball")
        self.testNpc2.init_inventory([item])
        parse_result = ParseResult(verb="give", unparsed="bowling ball to TestNpc")
        self.testNpc.notify_action(parsed=parse_result, actor=self.testNpc2)

        assert(quest.status == QuestStatus.COMPLETED)
        assert(self.testNpc2.search_item("bowling ball") == None) # npc will still accept the item
        assert(self.testNpc.quest == None)

class TestTalkQuest():

    d = Driver()
    llm_util = LlmUtil(FakeIoUtil(response='{"response": "ok", "give":"", "sentiment":"pleased"}'))
    llm_util.set_story(DynamicStory())
    d.llm_util = llm_util

    testNpc = LivingNpc("TestNpc", "m", age=20)
    testNpc2 = LivingNpc("TestNpc2", "m", age=20)

    def test_talk_quest(self):
        quest = Quest(name="TestQuest", reason="out of bowling balls", reward=100, giver=self.testNpc.name, type=QuestType.TALK, target="TestNpc")
        quest.set_status(QuestStatus.NOT_COMPLETED)
        self.testNpc.quest = quest

        parse_result = ParseResult(verb="say", unparsed="TestNpc: how are you?")
        self.testNpc.notify_action(parsed=parse_result, actor=self.testNpc2)

        assert(quest.status == QuestStatus.COMPLETED)
        assert(self.testNpc.quest == None)

    def test_talk_quest_greet(self):
        self.testNpc = LivingNpc("TestNpc", "m", age=20)
        quest = Quest(name="TestQuest", reason="out of bowling balls", reward=100, giver=self.testNpc.name, type=QuestType.TALK, target="TestNpc")
        quest.set_status(QuestStatus.NOT_COMPLETED)
        self.testNpc.quest = quest

        parse_result = ParseResult(verb="greet", unparsed="TestNpc: how are you?")
        self.testNpc.notify_action(parsed=parse_result, actor=self.testNpc2)

        assert(quest.status == QuestStatus.COMPLETED)
        assert(self.testNpc.quest == None)

    def test_talk_quest_not_started(self):
        """ Talking to a npc will start the quest, if it is not started."""
        self.testNpc = LivingNpc("TestNpc", "m", age=20)
        quest = Quest(name="TestQuest", reason="out of bowling balls", reward=100, giver=self.testNpc.name, type=QuestType.TALK, target="TestNpc")
        quest.set_status(QuestStatus.NOT_STARTED)
        self.testNpc.quest = quest

        parse_result = ParseResult(verb="greet", unparsed="TestNpc: how are you?")
        self.testNpc.notify_action(parsed=parse_result, actor=self.testNpc2)

        assert(quest.status == QuestStatus.NOT_COMPLETED)
        assert(self.testNpc.quest == quest)

class TestGenerateQuests():

    story = DynamicStory()
    story.catalogue.add_item({"name":"bowling ball", "description":"bowling ball"})
    story.catalogue.add_creature({"name":"goblin", "description":"goblin"})
    story.world.add_npc(LivingNpc("TalkToNpc", "m", age=20))

    def test_generate_give_quest(self):
        """ Test that a give quest is generated correctly."""
        quest = self.story.generate_quest(npc=TestGiveQuest.testNpc, type=QuestType.GIVE)

        assert(quest.type == QuestType.GIVE)
        assert(quest.target == "bowling ball")
        assert(quest.giver == TestGiveQuest.testNpc.name)

    def test_generate_talk_quest(self):
        """ Test that a talk quest is generated correctly."""
        quest = self.story.generate_quest(npc=TestGiveQuest.testNpc, type=QuestType.TALK)

        assert(quest.type == QuestType.TALK)
        assert(quest.target == "talktonpc")
        assert(quest.giver == TestGiveQuest.testNpc.name)

    def test_generate_kill_quest(self):
        """ Test that a kill quest is generated correctly."""
        quest = self.story.generate_quest(npc=TestGiveQuest.testNpc, type=QuestType.KILL)

        assert(quest.type == QuestType.KILL)
        assert(quest.target == "goblin")
        assert(quest.giver == TestGiveQuest.testNpc.name)
            
