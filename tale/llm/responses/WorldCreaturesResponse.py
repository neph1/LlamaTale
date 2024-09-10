

class WorldCreaturesResponse():

    def __init__(self, response: dict = {}):
        self.creatures = response.get("creatures", [])
        self.valid = len(self.creatures) > 0