import random

from tale import mud_context
from tale.base import Container, Location
from tale.util import call_periodically
from tale.zone import Zone


class ItemSpawner():
    def __init__(self, items: list, item_probabilities: list, zone: Zone, spawn_rate: int, container: Container = None, max_items: int = 1):
        self.items = items
        self.item_probabilities = item_probabilities
        self.zone = zone
        self.container = container
        self.max_items = max_items
        self.spawn_rate = spawn_rate
        self.time = 0
        mud_context.driver.register_periodicals(self)

    @call_periodically(15)
    def spawn(self):
        self.time += 15
        if self.time < self.spawn_rate:
            return
        self.time -= self.spawn_rate
        item = random.choices(self.items, weights=self.item_probabilities)[0]
        
        if self.container:
            self.container.insert(item, None)
        else:
            location = random.choice(list(self.zone.locations.values())) # type: Location
            if len(location.items) < self.max_items:
                location.insert(item, None)
                location.tell(f'{item} appears.')
    
    def to_json(self):
        data = {
            'items': [item.name for item in self.items],
            'item_probabilities': self.item_probabilities,
            'zone': self.zone.name,
            'spawn_rate': self.spawn_rate,
            'container': self.container.name if self.container else None,
            'max_items': self.max_items
        }
        return data