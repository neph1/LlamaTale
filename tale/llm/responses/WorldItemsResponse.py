

class WorldItemsResponse():

    def __init__(self, response: dict = {}):
        self.items = response.get("items", [])
        self.valid = len(self.items) > 0