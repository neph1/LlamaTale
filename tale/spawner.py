

from functools import wraps
import random

from tale import mud_context
from tale.base import Living, Location
from tale.util import call_periodically

class MobSpawner():
    def __init__(self, mob_type: Living , location: Location, spawn_rate: int, spawn_limit: int):
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
            mob.on_death_callback = lambda: self.remove_mob()
            self.location.insert(mob)
            self.location.tell("%s arrives." % mob.title, extra_context=f'Location:{self.location.description}; {mob.title}: {mob.description}')
            return mob
        return None
    
    def remove_mob(self):
        self.spawned -= 1

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
            "randomize_stats": self.randomize_stats

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

    def _clone_mob(self):
        gender = self.mob_type.gender
        if self.randomize_gender:
            gender = "m" if random.randint(0, 1) == 0 else "f"
        mob = self.mob_type.__class__(self.mob_type.name, gender)
        mob.aggressive = self.mob_type.aggressive
        mob.should_produce_remains = self.mob_type.should_produce_remains
        return mob
