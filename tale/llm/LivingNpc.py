import random
from tale.llm.action_executor import ActionExecutor
from tale.llm.character_card import CharacterCard
from tale.llm.event_memory import EventMemory
from tale.llm.item_handling_result import ItemHandlingResult
from tale.llm.npc_agent import NpcAgent
from tale import lang, mud_context
from tale.base import ContainingType, Living, ParseResult
from tale.errors import LlmResponseException
from tale.llm.responses.ActionResponse import ActionResponse
from tale.llm.responses.FollowResponse import FollowResponse
from tale.player import Player


from typing import Sequence

from tale.quest import Quest
from tale.resources_utils import pad_text_for_avatar, unpad_text
from tale.skills.magic import MagicType
from tale.skills.skills import SkillType
from tale.skills.weapon_type import WeaponType


class LivingNpc(Living):
    """An NPC with extra fields to define personality and help LLM generate dialogue.

    LLM interactions go through `self.agent` (NpcAgent) and all remembered state
    lives in `self.memory` (EventMemory); the attributes below delegate to the
    memory for backward compatibility.
    """

    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int = -1, personality: str="", occupation: str="", race: str="", parse_occupation: bool = False,
                 memory: EventMemory = None, agent: NpcAgent = None, executor: ActionExecutor = None):
        super(LivingNpc, self).__init__(name=name, gender=gender, title=title, descr=descr, short_descr=short_descr, race=race)
        self.memory = memory or EventMemory()
        self.agent = agent or NpcAgent()
        self.action_executor = executor or ActionExecutor(self)
        self.age = age
        self.personality = personality
        self.occupation = occupation
        self.quest = None # type: Quest # a quest object
        self.deferred_actions = set() # type: set[str]
        self.example_voice = '' # type: str
        self.autonomous = False
        self.output_thoughts = False
        if parse_occupation:
            self._parse_occupation(occupation)

    # -- memory-backed state, delegated to self.memory (EventMemory) --

    @property
    def known_locations(self) -> dict:
        return self.memory.known_locations

    @known_locations.setter
    def known_locations(self, value: dict) -> None:
        self.memory.known_locations = value

    @property
    def _observed_events(self) -> list:
        # hashed values of actions the character has been notified of
        return self.memory.events

    @_observed_events.setter
    def _observed_events(self, value) -> None:
        self.memory.events = list(value)

    @property
    def sentiments(self) -> dict:
        return self.memory.sentiments

    @sentiments.setter
    def sentiments(self, value: dict) -> None:
        self.memory.sentiments = value

    @property
    def action_history(self) -> list:
        return self.memory.action_history

    @action_history.setter
    def action_history(self, value) -> None:
        self.memory.action_history = list(value)

    @property
    def planned_actions(self) -> list:
        return self.memory.planned_actions

    @planned_actions.setter
    def planned_actions(self, value) -> None:
        self.memory.planned_actions = list(value)

    @property
    def goal(self):
        return self.memory.goal

    @goal.setter
    def goal(self, value) -> None:
        self.memory.goal = value

    def _parse_occupation(self, occupation: str) -> None:
        """ Parse the occupation of the npc."""
        if occupation in ['soldier', 'guard', 'mercenary', 'knight', 'warrior']: # Warrior
            self.stats.weapon_skills.set(WeaponType.ONE_HANDED, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.TWO_HANDED, random.randint(15, 30) + random.randint(0, 3) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.UNARMED, random.randint(30, 60))
            return
        if occupation in ['archer', 'ranger', 'hunter', 'marksman']: # Archer
            self.stats.weapon_skills.set(WeaponType.ONE_HANDED, random.randint(15, 30) + random.randint(0, 3) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.ONE_HANDED_RANGED, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.TWO_HANDED_RANGED, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.UNARMED, random.randint(30, 50))
            return
        if occupation in ['mage', 'sorcerer', 'wizard', 'warlock']: # Caster
            self.stats.magic_skills.set(MagicType.BOLT, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.magic_skills.set(MagicType.DRAIN, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.magic_skills.set(MagicType.REVEAL, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.UNARMED, random.randint(15, 30))
            return
        if occupation in ['healer', 'cleric', 'priest', 'monk']: # Healer
            self.stats.magic_skills.set(MagicType.HEAL, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.magic_skills.set(MagicType.REJUVENATE, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.magic_skills.set(MagicType.REVEAL, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            return
        if occupation in ['thief', 'rogue', 'assassin', 'bandit']: # Rogue
            self.stats.weapon_skills.set(WeaponType.UNARMED, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.ONE_HANDED, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.THROWING, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.skills.set(SkillType.HIDE, random.randint(30, 50) + random.randint(0, 5) * self.stats.level)
            self.stats.skills.set(SkillType.SEARCH, random.randint(20, 40) + random.randint(0, 5) * self.stats.level)
            self.stats.skills.set(SkillType.PICK_LOCK, random.randint(20, 40) + random.randint(0, 5) * self.stats.level)
            return
        if occupation in ['peasant', 'farmer', 'commoner', 'villager']:
            self.stats.weapon_skills.set(WeaponType.ONE_HANDED, random.randint(15, 30) + random.randint(0, 3) * self.stats.level)
            self.stats.weapon_skills.set(WeaponType.UNARMED, random.randint(30, 40))
            self.stats.weapon_skills.set(WeaponType.THROWING, random.randint(15, 30) + random.randint(0, 5) * self.stats.level)
            self.stats.skills.set(SkillType.SEARCH, random.randint(15, 30) + random.randint(0, 5) * self.stats.level)
            return

    def notify_action(self, parsed: ParseResult, actor: Living) -> None:
        # store even our own events.
        if actor is self or parsed.verb in self.verbs:
            return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        greet = False
        targeted = False
        for alias in self.aliases:
            if alias in parsed.unparsed:
                targeted = True
        if self.name in parsed.unparsed or self in parsed.who_info or self.title in parsed.unparsed:
            targeted = True
        if parsed.verb in ("hi", "hello") or parsed.verb == "greet":
            greet = True
        if greet and targeted:
            if self.quest:
                self.quest.check_completion({"npc":self.title})
            self.do_say(parsed.unparsed, actor)
        elif parsed.verb == "say" and targeted:
            if self.quest:
                self.quest.check_completion({"npc":self.title})
            self.do_say(parsed.unparsed, actor)
            
        elif (targeted and parsed.verb == "idle-action") or parsed.verb == "location-event":
            self.memory.observe(unpad_text(parsed.unparsed))
            self._do_react(parsed, actor)
        elif targeted and parsed.verb == "give":
            parsed_split = parsed.unparsed.split(" to ")
            
            if len(parsed_split) == 2:
                result = ItemHandlingResult(item=parsed_split[0], to=self.title)
            else:
                parsed_split = parsed.unparsed.split(self.title)
                if len(parsed_split[0]) == 0:
                    result = ItemHandlingResult(item=parsed_split[1].strip(), to=self.title)
                else:
                    result = ItemHandlingResult(item=parsed_split[0].strip(), to=self.title)
            if self.handle_item_result(result, actor) and self.quest:
                self.quest.check_completion({"item":result.item, "npc":result.to})
            self.do_say(parsed.unparsed, actor)
        elif parsed.verb == 'attack' and targeted:
            self.memory.observe(unpad_text(parsed.unparsed))
            # TODO: should llm decide sentiment?
            self.memory.set_sentiment(actor.title, 'hostile')
        elif parsed.verb == 'request_to_follow' and targeted:
            result = self.agent.request_follow(actor=actor,
                                               character_name=self.title,
                                               character_card=self.character_card,
                                               event_history=self.memory.observed_events(),
                                               location=self.location,
                                               asker_reason=parsed.args[0] if parsed.args else '') # type: FollowResponse
            if result:
                if result.follow:
                    self.following = actor
                    actor.tell(f"{self.title} starts following you.", evoke=False)
                if result.reason:
                    response = '{actor.title} says: "{response}"'.format(actor=self, response=("Yes. " if result.follow else "No. ") + result.reason)
                    self.memory.observe(response)
                    actor.tell(response, evoke=False)
                
        else:
            self.memory.observe(unpad_text(parsed.unparsed))
        if self.quest and self.quest.is_completed():
            # do last to give npc chance to react   
            self._clear_quest()
    
    def do_say(self, what_happened: str, actor: Living) -> None:
        self.memory.observe('{actor.title} says {what_happened}'.format(actor=actor, what_happened=unpad_text(what_happened)))
        short_len = False if isinstance(actor, Player) else True
        item = None
        sentiment = None
        response = None
        for i in range(3):
            response, item, sentiment = self.agent.generate_dialogue(
                conversation=self.memory.observed_events(),
                character_card=self.character_card,
                character_name=self.title,
                target=actor.title,
                target_description=actor.short_description,
                sentiment=self.memory.get_sentiment(actor.title),
                location_description=self.location.look(exclude_living=self),
                short_len=short_len)
            if response:
                if not self.avatar:
                    if self.agent.generate_image(self.name, self.description):
                        self.avatar = self.name
                break
        if not response:
            raise LlmResponseException("Failed to parse dialogue")

        self.memory.observe('{actor.title} says: {response}'.format(actor=self, response=unpad_text(response)))
        self._defer_result(response, verb='say')
        if item:
            self.handle_item_result(ItemHandlingResult(item=item, from_=self.title, to=actor.title), actor)

        if sentiment:
            self.memory.set_sentiment(actor.title, sentiment)

    def _do_react(self, parsed: ParseResult, actor: Living) -> None:
        if self.autonomous:
            action = self.autonomous_action()
        else:
            action = self.agent.perform_reaction(action=parsed.unparsed,
                                            character_card=self.character_card,
                                            character_name=self.title,
                                            location=self.location,
                                            acting_character_name=actor.title if actor else '',
                                            event_history=self.memory.observed_events(),
                                            sentiment=self.memory.get_sentiment(actor.title) if actor else '')
        if action:
            self.memory.add_action(action)
            self._defer_result(action, verb='reaction')

    def handle_item_result(self, result: ItemHandlingResult, actor: Living) -> bool:
        if result.to == self.title:
            item = actor.search_item(result.item)
            if not item:
                return False # fail silently
            actor.remove(item, actor=actor)
            item.move(target=self, actor=self)
            self._defer_result("%s gives %s to {Actor}" % (self.title, item.title), verb='give')
            return True

        if result.from_  == self.title:
            item = self.search_item(result.item)
            if not item:
                return False # fail silently
            self.remove(item, actor=self)
            if result.to:
                if result.to == actor.name or result.to == actor.title:
                    target = actor
                elif result.to in ["user", "you", "player"] and isinstance(actor, Player):
                    target = actor
                else:
                    target = self.location.search_living(result.to)
                if not target:
                    return False
                item.move(target=target, actor=target)
                self._defer_result("{Actor} gives %s to %s" % (item.title, actor.title), verb='give')
                actor.tell("%s gives you %s." % (self.subjective, item.title), evoke=False)
                return True
            else:
                item.move(self.location, self)
                self._defer_result("{Actor} drops %s on the floor" % (item.title), verb='put')
                return True
        return False

    def move(self, target: ContainingType, actor: Living=None,
             *, silent: bool=False, is_player: bool=False, verb: str="move", direction_names: Sequence[str]=None) -> None:
        self.known_locations[self.location.name] = f"description: {self.location.description}. " + ". ".join(self.location.look(exclude_living=self, short=True))
        super().move(target, actor, silent=silent, is_player=is_player, verb=verb, direction_names=direction_names)

    def idle_action(self):
        """ Plan and perform idle actions.
            Plans several actions in advance, then performs one per call.
        """
        if not self.planned_actions:
            previous_actions = self.memory.recent_actions(5)
            if self.autonomous:
                actions = [self.autonomous_action()]
            else:
                actions = self.agent.perform_idle_action(character_card=self.character_card,
                                                    character_name=self.title,
                                                    location=self.location,
                                                    last_action=previous_actions,
                                                    event_history=self.memory.observed_events(),
                                                    sentiments=self.sentiments)
            if actions:
                self.memory.plan(actions)
        action = self.memory.next_planned()
        if action:
            self.memory.add_action(action)
            self._defer_result(action)
            return action
        return None

    def autonomous_action(self) -> str:
        actions = self.agent.free_form_action(character_card=self.character_card,
                                            character_name=self.title,
                                            location=self.location,
                                            event_history=self.memory.observed_events()) # type: list
        if not actions:
            return None

        self.planned_actions.append(actions)

        defered_actions = []
        defered_actions.extend(self._parse_action(actions.pop(0)))

        return '\n'.join(defered_actions)
    
    def _parse_action(self, action: ActionResponse) -> list:
        """Execute a structured LLM action. Delegates to the ActionExecutor."""
        return self.action_executor.execute(action)

    def _defer_result(self, action: str, verb: str="idle-action"):
        """ Defer an action to be performed at the next tick, 
            or immediately if the server tick method is set to command"""
        if mud_context.config.custom_resources and self.avatar:
            action = pad_text_for_avatar(text=action, npc_name=self.title)
        else:
            action = f"{self.title} : {action}"
        self.deferred_actions.add(action)
        self.tell_action_deferred(verb)

    def tell_action_deferred(self, verb: str):
        actions = '\n'.join(self.deferred_actions) + '\n\n'
        actions = unpad_text(actions)
        actions = actions.replace('\n\n\n', '\n\n')
        deferred_action = ParseResult(verb=verb, unparsed=actions, who_info=None)
        self.tell_others(actions)
        self.location._notify_action_all(deferred_action, actor=self)
        self.deferred_actions.clear()

    def get_observed_events(self, amount: int) -> list:
        """ Returns the last amount of observed events as a single string"""
        return self.memory.observed_events(amount)

    def _clear_quest(self):
        self.quest = None

    @property
    def character_card(self) -> dict:
        data = CharacterCard(
            name=self.title,
            gender=lang.gender_string(self.gender),
            age=self.age,
            occupation=self.occupation,
            personality=self.personality,
            appearance=self.description,
            items=[str(i.name) for i in self.inventory],
            race=self.stats.race,
            quest=self.quest,
            goal=self.goal,
            example_voice=self.example_voice,
            wearing=[str(i.name) for i in self.get_worn_items()],
            wielding=self.wielding.to_dict() if self.wielding else None,
            roleplay_prompt=self.roleplay_prompt,
            roleplay_description=self.roleplay_description
        )
        return data
    
    def dump_memory(self) -> dict:
        return self.memory.dump()

    def load_memory(self, memory: dict):
        self.memory.load(memory)

        