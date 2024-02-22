

from typing import Type
from tale.base import Living, Location
from tale.util import call_periodically


class MobSpawner():
    def __init__(self, mob_type: Type['Living'] , location: Location, spawn_rate: int, spawn_limit: int):
        self.mob_type = mob_type # type 
        self.location = location
        self.spawn_rate = spawn_rate
        self.spawn_limit = spawn_limit
        self.spawned = 0

    def spawn(self):
        if self.spawned < self.spawn_limit:
            self.spawned += 1
            mob = self.mob_type()
            mob.do_on_death = self.remove_mob
            self.location.insert(mob)
            return mob
        return None
    
    def remove_mob(self, mob):
        self.spawned -= 1

    def reset(self):
        self.spawned = 0
        self.timer = 0

    def to_json(self):
        return {
            "mob_type": self.mob_type.__name__,
            "location": self.location.name,
            "spawn_rate": self.spawn_rate,
            "spawn_limit": self.spawn_limit,
            "spawned": self.spawned
        }
    
    def from_json(self, data):
        self.mob_type = data["mob_type"]
        self.location = data["location"]
        self.spawn_rate = data["spawn_rate"]
        self.spawn_limit = data["spawn_limit"]
        self.spawned = data["spawned"]

# Example usage
# spawner = MobSpawner("Zombie", 50, 10)
# spawner.spawn = call_periodically(40, 60)(spawner.spawn)