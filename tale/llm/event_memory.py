"""Memory store for an NPC: observed events, sentiments, action history,
planned actions, known locations and the current goal.

Extracted from LivingNpc so the state has one owner with capped growth and a
single dump/load implementation. Event strings are stored as hashes in the
global llm_cache; only the hashes live here.
"""

import tale.llm.llm_cache as llm_cache


class EventMemory:

    def __init__(self, max_events: int = 50, max_actions: int = 20):
        self.max_events = max_events
        self.max_actions = max_actions
        self.known_locations = {}      # type: dict[str, str]
        self.events = []               # type: list[int] # hashes into llm_cache.event_cache
        self.sentiments = {}           # type: dict[str, str]
        self.action_history = []       # type: list
        self.planned_actions = []      # type: list
        self.goal = None               # type: str # free form description of the npc's goal

    def observe(self, event: str) -> int:
        """Cache an event string and record its hash. Returns the hash."""
        event_hash = llm_cache.cache_event(event)
        self.events.append(event_hash)
        overflow = len(self.events) - self.max_events
        if overflow > 0:
            del self.events[:overflow]
        return event_hash

    def observed_events(self, amount: int = None) -> str:
        """Observed events joined into one string, optionally only the last `amount`."""
        hashes = self.events if amount is None else self.events[-amount:]
        return llm_cache.get_events(hashes)

    def add_action(self, action) -> None:
        """Record a performed action in the history (capped)."""
        self.action_history.append(action)
        overflow = len(self.action_history) - self.max_actions
        if overflow > 0:
            del self.action_history[:overflow]

    def recent_actions(self, amount: int = 5) -> list:
        """The last `amount` performed actions (or all, if fewer)."""
        if not self.action_history:
            return []
        return self.action_history[-amount:]

    def plan(self, actions) -> None:
        """Queue actions to be performed on later ticks."""
        self.planned_actions.append(actions)

    def next_planned(self):
        """Pop the next planned action. A queued list is unwrapped one element
        at a time; the remainder stays queued for later calls."""
        if not self.planned_actions:
            return None
        action = self.planned_actions.pop(0)
        if isinstance(action, list):
            if len(action) > 1:
                self.planned_actions.insert(0, action[1:])
            action = action[0] if len(action) > 0 else None
        return action

    def get_sentiment(self, key: str, default: str = '') -> str:
        return self.sentiments.get(key, default)

    def set_sentiment(self, key: str, value: str) -> None:
        self.sentiments[key] = value

    def dump(self) -> dict:
        return dict(
            known_locations=self.known_locations,
            observed_events=list(self.events),
            sentiments=self.sentiments,
            action_history=list(self.action_history),
            planned_actions=list(self.planned_actions),
            goal=self.goal)

    def load(self, memory: dict) -> None:
        self.known_locations = memory.get('known_locations', {})
        # 'conversations' is a legacy key from older savegames
        self.events = list(memory.get('observed_events', [])) + list(memory.get('conversations', []))
        self.sentiments = memory.get('sentiments', {})
        self.action_history = list(memory.get('action_history', []))
        self.planned_actions = list(memory.get('planned_actions', []))
        self.goal = memory.get('goal', None)
