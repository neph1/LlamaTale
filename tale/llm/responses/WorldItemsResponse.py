

class WorldItemsResponse():

    def __init__(self, response: dict = {}):
        self.items = response.get("items", [])
        self.valid = len(self.items) > 0
        self._validate_items()

    def _validate_items(self):
        for item in self.items:
            if item['type'] == 'Weapon' and not item.get('weapon_type', None):
                item['weapon_type'] = 'ONE_HANDED'