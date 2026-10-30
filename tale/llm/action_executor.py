"""Executes structured actions chosen by the LLM for an NPC.

ActionExecutor turns ActionResponse objects (produced via NpcAgent's
free_form_action) into world effects. Each known action name maps to a
handler method in the `handlers` registry; unknown actions fall back to
simple narration. LivingNpc._parse_action delegates here.
"""

from typing import TYPE_CHECKING

from tale.base import Door, ParseResult, Weapon
from tale.errors import ActionRefused
from tale.llm.item_handling_result import ItemHandlingResult
from tale.llm.responses.ActionResponse import ActionResponse
from tale.resources_utils import unpad_text

if TYPE_CHECKING:
    from tale.llm.LivingNpc import LivingNpc


class ActionExecutor:

    def __init__(self, npc: 'LivingNpc'):
        self.npc = npc
        self.handlers = {
            'move': self._act_move,
            'give': self._act_give,
            'take': self._act_take,
            'attack': self._act_attack,
            'wear': self._act_wear,
            'wield': self._act_wield,
            'remove': self._act_remove,
            'eat': self._act_consume,
            'drink': self._act_consume,
            'hide': self._act_hide,
            'unhide': self._act_unhide,
            'search': self._act_search,
            'pick_lock': self._act_pick_lock,
            # speech/emotes are handled by the text part of the action
            'say': self._act_noop,
            'emote': self._act_noop,
        }

    def execute(self, action: ActionResponse) -> list:
        """Perform the action. Returns deferred narration strings."""
        deferred = []
        if action.goal:
            self.npc.goal = action.goal
        if self.npc.output_thoughts and action.thoughts:
            self.npc.tell_others(f'\n{self.npc.title} thinks: *<it><rev> ' + action.thoughts + '</> *', evoke=False)
        if action.text:
            deferred.extend(self._do_text(action))
        handler = self.handlers.get(action.action)
        if handler:
            deferred.extend(handler(action) or [])
        elif action.action:
            deferred.append(f"{self.npc.title} {action.action}")
        return deferred

    def _do_text(self, action: ActionResponse) -> list:
        text = action.text
        self.npc.memory.observe('{actor.title} says: "{response}"'.format(actor=self.npc, response=unpad_text(text)))
        if action.action == 'emote':
            return [f"{self.npc.title} {text}"]
        if action.target:
            target = self.npc.location.search_living(action.target)
            if target:
                target.tell(text, evoke=False)
                target.notify_action(ParseResult(verb='say', unparsed=text, who_list=[target]), actor=self.npc)
                return []
        return [f'"{text}"']

    def _find_exit(self, target: str):
        """Find an exit by direction/alias name, or by target location name."""
        if not target or not self.npc.location:
            return None
        exits = self.npc.location.exits
        exit = exits.get(target) or exits.get(target.lower())
        if exit:
            return exit
        for e in exits.values():
            if e.target and e.target.name.lower() == target.lower():
                return e
        return None

    def _find_item(self, action: ActionResponse, include_inventory: bool, include_location: bool):
        name = action.item or action.target
        if not name:
            return None
        return self.npc.search_item(name, include_inventory=include_inventory, include_location=include_location)

    def _act_noop(self, action: ActionResponse) -> list:
        return []

    def _act_move(self, action: ActionResponse) -> list:
        exit = self._find_exit(action.target)
        if exit:
            self.npc.move(target=exit.target, actor=self.npc, direction_names=exit.names)
        return []

    def _act_give(self, action: ActionResponse) -> list:
        if action.item and action.target:
            result = ItemHandlingResult(item=action.item, to=action.target, from_=self.npc.title)
            self.npc.handle_item_result(result, actor=self.npc)
        return []

    def _act_take(self, action: ActionResponse) -> list:
        item = self._find_item(action, include_inventory=False, include_location=True)
        if item:
            item.move(target=self.npc, actor=self.npc)
            return [f"{self.npc.title} takes {item.title}"]
        return []

    def _act_attack(self, action: ActionResponse) -> list:
        if action.target:
            target = self.npc.location.search_living(action.target)
            if target:
                self.npc.start_attack(target)
                return [f"{self.npc.title} attacks {target.title}"]
        return []

    def _act_wear(self, action: ActionResponse) -> list:
        item = self._find_item(action, include_inventory=False, include_location=True)
        if item:
            self.npc.set_wearable(item)
            return [f"{self.npc.title} wears {item.title}"]
        return []

    def _act_wield(self, action: ActionResponse) -> list:
        item = self._find_item(action, include_inventory=True, include_location=True)
        if isinstance(item, Weapon):
            self.npc.wielding = item
            return [f"{self.npc.title} wields {item.title}"]
        return []

    def _act_remove(self, action: ActionResponse) -> list:
        name = (action.item or action.target or '').lower()
        if not name:
            return []
        for worn in self.npc.get_worn_items():
            if worn.name.lower() == name or name in worn.name.lower():
                wear_location = self.npc.get_wearable_location(worn.name)
                self.npc.set_wearable(None, wear_location=wear_location)
                return [f"{self.npc.title} removes {worn.title}"]
        return []

    def _act_consume(self, action: ActionResponse) -> list:
        item = self._find_item(action, include_inventory=True, include_location=True)
        if not item:
            return []
        try:
            item.consume(self.npc)
        except ActionRefused:
            return []
        return [f"{self.npc.title} {action.action}s {item.title}"]

    def _act_hide(self, action: ActionResponse) -> list:
        self.npc.hide()
        return []

    def _act_unhide(self, action: ActionResponse) -> list:
        self.npc.hide(False)
        return []

    def _act_search(self, action: ActionResponse) -> list:
        self.npc.search_hidden()
        return []

    def _act_pick_lock(self, action: ActionResponse) -> list:
        exit = self._find_exit(action.target)
        if isinstance(exit, Door) and exit.locked:
            try:
                self.npc.pick_lock(exit)
            except ActionRefused:
                pass
        return []
