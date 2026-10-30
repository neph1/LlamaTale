from typing import List
from tale.llm.schemas import DungeonLocationsSchema


class LocationDescriptionResponse():

    def __init__(self, model: DungeonLocationsSchema):
        self.location_descriptions = [
            LocationDescription(
                index=loc.index,
                name=loc.name,
                description=loc.description,
            )
            for loc in model.locations
        ]
        self.valid = len(self.location_descriptions) > 0


class LocationDescription():

    def __init__(self, index: int, name: str, description: str):
        self.index = index
        self.name = name
        self.description = description
