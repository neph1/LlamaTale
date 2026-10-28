from typing import List
from tale.llm.schemas import NpcSchema


class WorldCreaturesResponse():

    def __init__(self, creatures: List[NpcSchema] = None):
        self.creatures = [c.model_dump() for c in (creatures or [])]
        self.valid = len(self.creatures) > 0
