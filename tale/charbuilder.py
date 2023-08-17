"""
Character builder for multi-user mode.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

from typing import Generator, Set, Dict, Any

from . import lang
from . import mud_context
from .accounts import MudAccounts
from .base import Stats
from .player import Player, PlayerConnection
from .story import StoryConfig


class PlayerNaming:
    def __init__(self) -> None:
        self._name = self.title = self.gender = self.description = self.short_description = ""
        self.money = mud_context.config.player_money
        self.stats = Stats()
        self.wizard = False
        self.password = ""
        self.email = ""
        self.story_data = {}  # type: Dict[Any, Any]

    def apply_to(self, player: Player) -> None:
        assert self._name
        assert self.gender
        player.init_gender(self.gender)
        title = "" if self.title == self._name else self.title
        player.init_names(self._name, title, self.description, self.short_description)
        player.stats = self.stats
        player.money = self.money
        player.story_data = self.story_data

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str):
        self._name = value.lower()


class IFCharacterBuilder:
    """Create a new player character interactively."""
    def __init__(self, conn: PlayerConnection, config: StoryConfig) -> None:
        self.conn = conn
        self.config = config
        self.naming = PlayerNaming()

    def ask_name(self) -> Generator:
        self.conn.output("Creating a player character.\n")
        self.naming.name = yield "input", ("What shall you be known as?", MudAccounts.accept_name)

    def ask_credentials(self) -> Generator:
        yield from []

    def ask_confirm(self) -> Generator:
        # review the account
        self.conn.player.tell("<bright>Please review your choices.</>", end=True)
        self.conn.player.tell("<dim> name:</> %s,  <dim>gender:</> %s,  <dim>race:</> %s"
                              % (self.naming.name, lang.GENDERS[self.naming.gender], self.naming.stats.race), end=True)
        okay = yield "input", ("You cannot change your name later. Do you accept your choices?", lang.yesno)
        return okay

    def build_character(self) -> Generator:
        yield from self.ask_name()
        yield from self.ask_credentials()
        if len(self.config.playable_races) > 1:
            self.conn.player.tell("You can choose one of the following races: " + lang.join(self.config.playable_races))
            race = yield "input", ("What should be the race of your player character?", ValidRaceValidator(self.config.playable_races))
        else:
            race = self.config.playable_races[0]
        self.naming.gender = yield "input", ("What is the gender of your character (m/f)?", lang.validate_gender_mf)
        self.naming.stats = Stats.from_race(race, gender=self.naming.gender)
        self.naming.description = "A regular person." if self.naming.stats.race == "human" else "A weird creature."
        okay = yield from self.ask_confirm()
        return self.naming if okay else None


class MudCharacterBuilder(IFCharacterBuilder):
    """Create a new player character interactively."""
    def __init__(self, conn: PlayerConnection, name: str, config: StoryConfig) -> None:
        super().__init__(conn, config)
        self.naming.name = name

    def ask_name(self) -> Generator:
        self.conn.output("<ul><bright>New character creation: '%s'.</>\n" % self.naming.name)
        yield from []

    def ask_credentials(self) -> Generator:
        while True:
            password = yield "input-noecho", ("Please type in the desired password.", MudAccounts.accept_password)
            password2 = yield "input-noecho", ("Please retype the password.", MudAccounts.accept_password)
            if password != password2:
                self.conn.output("<it>The passwords don't match! Please try again.</>")
            else:
                break
        self.naming.password = password
        self.naming.email = yield "input", ("Please type in your email address.", MudAccounts.accept_email)

    def ask_confirm(self) -> Generator:
        # review the account
        self.conn.player.tell("<bright>Please review your new character.</>", end=True)
        self.conn.player.tell("<dim> name:</> %s,  <dim>gender:</> %s,  <dim>race:</> %s"
                              % (self.naming.name, lang.GENDERS[self.naming.gender], self.naming.stats.race), end=True)
        self.conn.player.tell("<dim> email:</> " + self.naming.email, end=True)
        okay = yield "input", ("You cannot change your name later. Do you want to create this character?", lang.yesno)
        if okay:
            return True
        self.conn.player.tell("<it>Ok, let's get back to the beginning then.</>", end=True)
        self.conn.player.tell("-- -- -- --", end=True)
        return False


class ValidRaceValidator:
    def __init__(self, valid_races: Set[str]) -> None:
        self.valid_races = valid_races

    def __call__(self, value: str) -> str:
        value = value.lower() if value else ""
        if value in self.valid_races:
            return value
        raise ValueError("That is not a valid race.")
