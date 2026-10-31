
from tale import mud_context
from tale.base import Location, Exit
from tale.demo.story import Story as DemoStory
from tale.web import web_utils
from tale.web.web_utils import create_chat_container, copy_single_image, _check_file_exists, direction_abbreviation, exits_for_web
from tests.supportstuff import FakeDriver


class TestWebUtils():

    def test_create_chat_container(self):
        result = create_chat_container("Bloated Murklin <:> Hello World!")

        assert "chat-container" in result
        assert '<div class="user-name" content="Bloated Murklin"></div>' in result
        assert '<div class="text-field" type="text">Hello World!</div>' in result

    # def test_copy_single_image(self):
    #     web_utils.web_resources_path = "tale/web"
    #     copy_single_image("./tests/files", "test.jpg")
    #     assert _check_file_exists("test.jpg")
    #     web_utils.clear_resources()


class TestDirectionAbbreviation():

    def test_known_directions(self):
        assert direction_abbreviation("north") == "n"
        assert direction_abbreviation("south") == "s"
        assert direction_abbreviation("Northeast") == "ne"
        assert direction_abbreviation("up") == "u"
        assert direction_abbreviation("down") == "d"
        assert direction_abbreviation("in") == "in"
        assert direction_abbreviation("out") == "out"

    def test_unknown_or_empty(self):
        assert direction_abbreviation("") == ""
        assert direction_abbreviation("kitchen") == ""


class TestExitsForWeb():

    def setup_method(self, method):
        mud_context.driver = FakeDriver()
        mud_context.config = DemoStory().config
        mud_context.resources = mud_context.driver.resources

    def test_location_named_exit_with_direction(self):
        # json-story style exit: named after the target location, with a direction alias
        hall = Location("hall")
        kitchen = Location("kitchen")
        hall.add_exits([Exit(["kitchen", "north"], kitchen, "A doorway leads north to the kitchen.")])

        assert exits_for_web(hall) == [{"name": "kitchen", "direction": "n"}]

    def test_direction_named_exit_has_no_direction_suffix(self):
        # python-story style exit: the exit name itself is the direction
        hall = Location("hall")
        street = Location("street")
        hall.add_exits([Exit(["east", "e"], street, "A street to the east.")])

        assert exits_for_web(hall) == [{"name": "east", "direction": ""}]

    def test_exit_without_direction(self):
        hall = Location("hall")
        grotto = Location("Royal Grotto")
        hall.add_exits([Exit("Royal Grotto", grotto, "An opening leads deeper into the cave.")])

        assert exits_for_web(hall) == [{"name": "royal grotto", "direction": ""}]

    def test_invisible_exits_are_skipped_and_aliases_not_duplicated(self):
        hall = Location("hall")
        kitchen = Location("kitchen")
        attic = Location("attic")
        e1 = Exit(["kitchen", "north"], kitchen, "A doorway leads north to the kitchen.")
        e2 = Exit("up", attic, "A ladder leads up.")
        e2.visible = False
        hall.add_exits([e1, e2])

        assert exits_for_web(hall) == [{"name": "kitchen", "direction": "n"}]

    def test_empty_location(self):
        hall = Location("hall")
        assert exits_for_web(hall) == []