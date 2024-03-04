
import random

from tale import mud_context
from tale.base import Container, Living, Location
from tale.util import call_periodically

class MobSpawner():
    def __init__(self, mob_type: Living , location: Location, spawn_rate: int, spawn_limit: int, drop_items: list = None, drop_item_probabilities: list = None):
        self.mob_type = mob_type # type 'Living'
        self.location = location
        self.spawn_rate = spawn_rate
        self.spawn_limit = spawn_limit
        self.spawned = 0
        self.max_spawns = -1
        self.randomize_gender = True
        self.randomize_stats = True
        self.time = 0
        mud_context.driver.register_periodicals(self)
        self.drop_item_chance = 0.0
        if drop_items:
            self.drop_items = drop_items
            self.drop_item_probabilities = drop_item_probabilities
            self.drop_item_chance = sum(self.drop_item_probabilities)
        else:
            self.drop_items = None
            self.drop_item_probabilities = None
            

    @call_periodically(15)
    def spawn(self):
        self.time += 15
        if self.time < self.spawn_rate:
            return
        self.time -= self.spawn_rate
        if self.max_spawns == 0:
            return None
        if self.spawned < self.spawn_limit:
            self.spawned += 1
            if self.max_spawns > 0:
                self.max_spawns -= 1
            mob = self._clone_mob()
            mob.should_produce_remains = True
            mob.on_death_callback = lambda remains: self.remove_mob(remains)
            self.location.insert(mob)
            self.location.tell("%s arrives." % mob.title, extra_context=f'Location:{self.location.description}; {mob.title}: {mob.description}')
            return mob
        return None
    
    def remove_mob(self, remains: Container = None):
        self.spawned -= 1
        if remains and self.drop_item_chance > 0:
            if random.random() < self.drop_item_chance:
                item = random.choices(self.drop_items, weights=self.drop_item_probabilities)[0]
                remains.insert(item, actor=None)
                


    def reset(self):
        self.spawned = 0
        self.timer = 0

    def to_json(self):
        return {
            "mob_type": self.mob_type.name,
            "location": self.location.name,
            "spawn_rate": self.spawn_rate,
            "spawn_limit": self.spawn_limit,
            "spawned": self.spawned,
            "max_spawns": self.max_spawns,
            "randomize_gender": self.randomize_gender,
            "randomize_stats": self.randomize_stats,
            "drop_items": [item.name for item in self.drop_items] if self.drop_items else None,
            "drop_item_probabilities": self.drop_item_probabilities if self.drop_item_probabilities else None

        }
    
    def from_json(self, data):
        self.mob_type = data["mob_type"]
        self.location = data["location"]
        self.spawn_rate = data["spawn_rate"]
        self.spawn_limit = data["spawn_limit"]
        self.spawned = data["spawned"]
        self.max_spawns = data["max_spawns"]
        self.randomize_gender = data["randomize_gender"]
        self.randomize_stats = data["randomize_stats"]
        self.drop_items = data["drop_items"]
        self.drop_item_probabilities = data["drop_item_probabilities"]

    def _clone_mob(self):
        gender = self.mob_type.gender
        if self.randomize_gender:
            gender = "m" if random.randint(0, 1) == 0 else "f"
        mob = self.mob_type.__class__(self.mob_type.name, gender, race=self.mob_type.stats.race)
        mob.aggressive = self.mob_type.aggressive
        mob.should_produce_remains = self.mob_type.should_produce_remains
        return mob
