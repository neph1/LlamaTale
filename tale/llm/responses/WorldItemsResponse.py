

class WorldItemsResponse():

    def __init__(self, response: dict = {}):
        self.items = response["items"]
        self.valid = len(self.items) > 0