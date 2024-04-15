


class LocationDescriptionResponse():

    def __init__(self, response: dict):
        response = self._sanitize_room_descriptions(response)
        assert isinstance(response, list), f"Expected a list of rooms, got {response}"
        self.location_descriptions = []
        for location in response:
            self.location_descriptions.append(LocationDescription(index=location.get('index', 0), name=location.get('name', ''), description=location.get('description', '')))
            
        
    def _sanitize_room_descriptions(self, parsed):
        if isinstance(parsed, dict):
            if "rooms" in parsed:
                return parsed["rooms"]
            elif "locations" in parsed:
                return parsed["locations"]
            elif len(parsed.values()) > 1:
                return list(parsed.values())
            else:
                return parsed
        elif isinstance(parsed, list):
            return parsed
        return []
    
class LocationDescription():

    def __init__(self, index: int, name: str, description: str):
        self.index = index
        self.name = name
        self.description = description