import tale.llm.llm_cache as llm_cache
from tale import lang, mud_context
from tale.base import ContainingType, Living, ParseResult
from tale.errors import TaleError
from tale.player import Player


from typing import Sequence


class LivingNpc(Living):
    """An NPC with extra fields to define personality and help LLM generate dialogue"""

    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str, occupation: str="", race: str=""):
        super(LivingNpc, self).__init__(name=name, gender=gender, title=title, descr=descr, short_descr=short_descr, race=race)
        self.age = age
        self.personality = personality
        self.occupation = occupation
        self.known_locations = dict()
        self._observed_events = set() # type: set[int] # These are hashed values of action the character has been notified of
        self._conversations = set() # type: set[str] # These are hashed values of conversations the character has involved in
        self.sentiments = {}
        self.action_history = [] # type: list[str]
        self.planned_actions = [] # type: list[str]
        self.goal = None # type: str # a free form string describing the goal of the NPC

    def notify_action(self, parsed: ParseResult, actor: Living) -> None:
        # store even our own events.
        event_hash = llm_cache.cache_event(parsed.unparsed)
        self._observed_events.add(event_hash)

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
            self.tell_others("{Actor} says: \"Hi.\"", evoke=True)
            #self.update_conversation(f"{self.title} says: \"Hi.\"")
        elif parsed.verb == "say" and targeted:
            self.do_say(parsed.unparsed, actor)
        elif targeted and parsed.verb == "idle-action":
            self._do_react(parsed, actor)

    def do_say(self, what_happened: str, actor: Living) -> None:
        tell_hash = llm_cache.cache_tell('{actor.title}:{what_happened}'.format(actor=actor, what_happened=what_happened))
        self._conversations.add(tell_hash)
        short_len = False if isinstance(actor, Player) else True

        response, item_result, sentiment = mud_context.driver.llm_util.generate_dialogue(
            conversation=llm_cache.get_tells(self._conversations),
            character_card = self.character_card,
            character_name = self.title,
            target = actor.title,
            target_description = actor.short_description,
            sentiment = self.sentiments.get(actor.title, ''),
            location_description=self.location.look(exclude_living=self),
            event_history=llm_cache.get_events(self._observed_events),
            short_len=short_len)

        # if summary:
        #     self.update_conversation(f"{self.title} says: \"{summary}\"")
        # else:

        tell_hash = llm_cache.cache_tell('{actor.title}:{response}'.format(actor=self.title, response=response))
        self._conversations.add(tell_hash)
        self.tell_others("{response}".format(response=response), evoke=False)
        if item_result:
            self.handle_item_result(item_result, actor)

        if sentiment:
            self.sentiments[actor.title] = sentiment

    def _do_react(self, parsed: ParseResult, actor: Living) -> None:
        action = mud_context.driver.llm_util.perform_reaction(action=parsed.unparsed,
                                            character_card=self.character_card,
                                            character_name=self.title,
                                            location=self.location,
                                            acting_character_name=actor.title,
                                            event_history=llm_cache.get_events(self._observed_events),
                                            sentiment=self.sentiments.get(actor.name, ''))
        if action:
            self.action_history.append(action)
            result = ParseResult(verb='idle-action', unparsed=action, who_info=None)
            self.tell_others(action)
            self.location._notify_action_all(result, actor=self)

    def handle_item_result(self, result: str, actor: Living):

        if result["from"] == self.title:
            item = self.search_item(result["item"])
            if not item:
                raise TaleError("item not found on actor %s " % item)
            if result["to"]:

                if result["to"] == actor.name or result["to"] == actor.title:
                    item.move(actor, self)
                elif result["to"] in ["user", "you", "player"] and isinstance(actor, Player):
                    item.move(actor, self)
                actor.tell("%s gives you %s." % (self.subjective, item.title), evoke=False)
                self.tell_others("{Actor} gives %s to %s" % (item.title, actor.title), evoke=False)
            else:
                item.move(self.location, self)
                self.tell_others("{Actor} drops %s on the floor" % (item.title), evoke=False)

    def move(self, target: ContainingType, actor: Living=None,
             *, silent: bool=False, is_player: bool=False, verb: str="move", direction_names: Sequence[str]=None) -> None:
        self.known_locations[self.location.name] = f"description: {self.location.description}. " + ". ".join(self.location.look(exclude_living=self, short=True))
        super().move(target, actor, silent=silent, is_player=is_player, verb=verb, direction_names=direction_names)

    def idle_action(self):
        """ Plan and perform idle actions. 
            Currently handles planning several actions in advance, and then performing them in reverse order.
        """
        if not self.planned_actions:
            if self.action_history:
                history_length = len(self.action_history)
                previous_actions = self.action_history[-5:] if history_length > 4 else self.action_history[-history_length:]
            else:
                previous_actions = []
            actions = mud_context.driver.llm_util.perform_idle_action(character_card=self.character_card,
                                                character_name=self.title,
                                                location=self.location,
                                                last_action=previous_actions,
                                                event_history=llm_cache.get_events(self._observed_events),
                                                sentiments=self.sentiments)
            if actions:
                self.planned_actions.append(actions)
        if len(self.planned_actions) > 0:
            action = self.planned_actions.pop(0)
            self.action_history.append(action)
            result = ParseResult(verb='idle-action', unparsed=action, who_info=None)
            self.tell_others(action)
            self.location.notify_action(result, actor=self)
            self.location._notify_action_all(result, actor=self)

    def travel(self):
        result = mud_context.driver.llm_util.perform_travel_action(character_card=self.character_card,
                                            character_name=self.title,
                                            location=self.location,
                                            locations=', '.join(self.location.exits.keys()),
                                            directions=[])
        if result:
            exit = self.location.exits.get(result)
            if exit:
                self.move(target=exit.target, actor=self)

    @property
    def character_card(self) -> str:
        items = []
        for i in self.inventory:
            items.append(f'"{str(i.name)}"')
        return '{{"name":"{name}", "gender":"{gender}","age":{age},"occupation":"{occupation}","personality":"{personality}","appearance":"{description}","items":[{items}], "race":"{race}"}}'.format(
                name=self.title,
                gender=lang.gender_string(self.gender),
                age=self.age,
                personality=self.personality,
                description=self.description,
                occupation=self.occupation,
                race=self.stats.race,
                items=','.join(items))
    
    def dump_memory(self) -> dict:
        return dict(
                    known_locations=self.known_locations,
                    observed_events=llm_cache.get_events(self._observed_events),
                    conversations=llm_cache.get_tells(self._conversations),
                    sentiments=self.sentiments,
                    action_history=self.action_history,
                    planned_actions=self.planned_actions,
                    goal=self.goal)
    
    def load_memory(self, memory: dict):
        self.known_locations = memory.get('known_locations', {})
        self._observed_events = set([llm_cache.cache_event(event) for event in memory.get('observed_events', [])])
        self._conversations = set([llm_cache.cache_tell(tell) for tell in memory.get('conversations', [])])
        self.sentiments = memory.get('sentiments', {})
        self.action_history = memory.get('action_history', [])
        self.planned_actions = memory.get('planned_actions', [])
        self.goal = memory.get('goal', None)