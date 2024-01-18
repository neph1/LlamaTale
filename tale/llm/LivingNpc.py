from tale.llm.item_handling_result import ItemHandlingResult
import tale.llm.llm_cache as llm_cache
from tale import lang, mud_context
from tale.base import ContainingType, Living, ParseResult
from tale.errors import LlmResponseException
from tale.player import Player


from typing import Sequence

from tale.quest import Quest
from tale.resources_utils import pad_text_for_avatar, unpad_text


class LivingNpc(Living):
    """An NPC with extra fields to define personality and help LLM generate dialogue"""

    def __init__(self, name: str, gender: str, *,
                 title: str="", descr: str="", short_descr: str="", age: int, personality: str="", occupation: str="", race: str=""):
        super(LivingNpc, self).__init__(name=name, gender=gender, title=title, descr=descr, short_descr=short_descr, race=race)
        self.age = age
        self.personality = personality
        self.occupation = occupation
        self.known_locations = dict()
        self._observed_events = [] # type: list[int] # These are hashed values of action the character has been notified of
        self._conversations = [] # type: list[str] # These are hashed values of conversations the character has involved in
        self.sentiments = {}
        self.action_history = [] # type: list[str]
        self.planned_actions = [] # type: list[str]
        self.goal = None # type: str # a free form string describing the goal of the NPC
        self.quest = None # type: Quest # a quest object
        self.deferred_actions = set() # type: set[str]
        self.autonomous = False

    def notify_action(self, parsed: ParseResult, actor: Living) -> None:
        # store even our own events.
        event_hash = llm_cache.cache_event(unpad_text(parsed.unparsed))
        self._observed_events.append(event_hash)
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
            # TODO: should llm decide sentiment?
            self.sentiments[actor.title] = 'hostile'
        if self.quest and self.quest.is_completed():
            # do last to give npc chance to react   
            self._clear_quest()
    
    def do_say(self, what_happened: str, actor: Living) -> None:
        tell_hash = llm_cache.cache_tell('{actor.title} says {what_happened}'.format(actor=actor, what_happened=unpad_text(what_happened)))
        self._conversations.append(tell_hash)
        short_len = False if isinstance(actor, Player) else True
        item = None
        sentiment = None
        for i in range(3):
            if self.autonomous:
                response = self.autonomous_action()
            else:
                response, item, sentiment = mud_context.driver.llm_util.generate_dialogue(
                    conversation=llm_cache.get_tells(self._conversations),
                    character_card = self.character_card,
                    character_name = self.title,
                    target = actor.title,
                    target_description = actor.short_description,
                    sentiment = self.sentiments.get(actor.title, ''),
                    location_description=self.location.look(exclude_living=self),
                    event_history=llm_cache.get_events(self._observed_events),
                    short_len=short_len)
            if response:
                if not self.avatar:
                    result = mud_context.driver.llm_util.generate_image(self.name, self.description)
                    if result:
                        self.avatar = self.name
                break
        if not response:
            raise LlmResponseException("Failed to parse dialogue")

        tell_hash = llm_cache.cache_tell('{actor.title} says: {response}'.format(actor=self, response=unpad_text(response)))
        self._conversations.append(tell_hash)
        self._defer_result(response, verb='say')
        if item:
            self.handle_item_result(ItemHandlingResult(item=item, from_=self.title, to=actor.title), actor)

        if sentiment:
            self.sentiments[actor.title] = sentiment

    def _do_react(self, parsed: ParseResult, actor: Living) -> None:
        if self.autonomous:
            action = self.autonomous_action()
        else: 
            action = mud_context.driver.llm_util.perform_reaction(action=parsed.unparsed,
                                            character_card=self.character_card,
                                            character_name=self.title,
                                            location=self.location,
                                            acting_character_name=actor.title if actor else '',
                                            event_history=llm_cache.get_events(self._observed_events),
                                            sentiment=self.sentiments.get(actor.name, '') if actor else '')
        if action:
            self.action_history.append(action)
            self._defer_result(action, verb='idle-action')

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
            Currently handles planning several actions in advance, and then performing them in reverse order.
        """
        if not self.planned_actions:
            if self.action_history:
                history_length = len(self.action_history)
                previous_actions = self.action_history[-5:] if history_length > 4 else self.action_history[-history_length:]
            else:
                previous_actions = []
            if self.autonomous:
                actions = [self.autonomous_action()]
            else: 
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
            if isinstance(action, list):
                action = action[0]
            self.action_history.append(action)
            self._defer_result(action)
            return action
        return None
            #self.location.notify_action(result, actor=self)

    def autonomous_action(self) -> str:
        action = mud_context.driver.llm_util.free_form_action(character_card=self.character_card,
                                            character_name=self.title,
                                            location=self.location,
                                            event_history=llm_cache.get_events(self._observed_events))
        if not action:
            return None
        
        defered_actions = []
        if action.get('text', ''):
            text = action['text']
            tell_hash = llm_cache.cache_tell('{actor.title} says: "{response}"'.format(actor=self, response=unpad_text(text)))
            self._conversations.append(tell_hash)
            #if mud_context.config.custom_resources:
            if action.get('target'):
                target = self.location.search_living(action['target'])
                if target:
                    #target.tell(text, evoke=False)
                    target.notify_action(ParseResult(verb='say', unparsed=text, who_list=[target]), actor=self)
            defered_actions.append(f'"{text}"')
        if not action.get('action', ''):
            return '\n'.join(defered_actions)
        if action['action'] == 'move':
            try:
                exit = self.location.exits[action['target']]
            except KeyError:
                exit = None
            if exit:
                self.move(target=exit.target, actor=self, direction_names=exit.names)
        elif action['action'] == 'give':
            result = ItemHandlingResult(item=action['item'], to=action['target'], from_=self.title)
            self.handle_item_result(result, actor=self)
        elif action['action'] == 'take':
            item = self.search_item(action['item'], include_location=True, include_inventory=False) # Type: Item
            if item:
                item.move(target=self, actor=self)
                defered_actions.append(f"{self.title} takes {item.title}")
        elif action['action'] == 'attack':
            target = self.location.search_living(action['target'])
            if target:
                self.start_attack(target)
                defered_actions.append(f"{self.title} attacks {target.title}")

        return '\n'.join(defered_actions)
    

    def _defer_result(self, action: str, verb: str="idle-action"):
        if mud_context.config.custom_resources and self.avatar:
            action = pad_text_for_avatar(text=action, npc_name=self.title)
        else:
            action = f"{self.title} : {action}"
        self.deferred_actions.add(action)
        mud_context.driver.defer(1.0, self.tell_action_deferred)

    def tell_action_deferred(self):
        actions = '\n'.join(self.deferred_actions)
        deferred_action = ParseResult(verb='idle-action', unparsed=actions, who_info=None)
        self.tell_others(actions + '\n')
        self.location._notify_action_all(deferred_action, actor=self)
        self.deferred_actions.clear()

    def get_observed_events(self, amount: int) -> list:
        """ Returns the last amount of observed events as a list of strings"""
        return llm_cache.get_events(self._observed_events[-amount:])

    def _clear_quest(self):
        self.quest = None

    @property
    def character_card(self) -> str:
        items = []
        for i in self.inventory:
            items.append(f'"{str(i.name)}"')
        return '{{"name":"{name}", "gender":"{gender}","age":{age},"occupation":"{occupation}","personality":"{personality}","appearance":"{description}","items":[{items}], "race":"{race}", "quest":"{quest}", "wearing":"{wearing}"}}'.format(
                name=self.title,
                gender=lang.gender_string(self.gender),
                age=self.age,
                personality=self.personality,
                description=self.description,
                occupation=self.occupation,
                race=self.stats.race,
                quest=self.quest,
                wearing=','.join([f'"{str(i.name)}"' for i in self.get_worn_items()]),
                items=','.join(items))
    
    def dump_memory(self) -> dict:
        return dict(
                    known_locations=self.known_locations,
                    observed_events=self._observed_events,
                    conversations=self._conversations,
                    sentiments=self.sentiments,
                    action_history=self.action_history,
                    planned_actions=self.planned_actions,
                    goal=self.goal)

    
    def load_memory(self, memory: dict):
        self.known_locations = memory.get('known_locations', {})
        self._observed_events = memory.get('observed_events', [])
        self._conversations = memory.get('conversations', [])
        self.sentiments = memory.get('sentiments', {})
        self.action_history = memory.get('action_history', [])
        self.planned_actions = memory.get('planned_actions', [])
        self.goal = memory.get('goal', None)