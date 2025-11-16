


class LocationDescriptionResponse():

    def __init__(self, response: dict):
        response = self._sanitize_room_descriptions(response)
        assert isinstance(response, list), f"Expected a list of rooms, got {response}"
        self.location_descriptions = []
        if not response:
            pass
        elif isinstance(response[0], dict):
            for location in response:
                self.location_descriptions.append(
                    LocationDescription(
                        index=location.get("index", 0),
                        name=location.get("name", ""),
                        description=location.get("description", ""),
                    )
                )
        elif isinstance(response[0], (list, tuple)):
            for location in response:
                idx = location[0] if len(location) > 0 else 0
                name = location[1] if len(location) > 1 else ""
                desc = location[2] if len(location) > 2 else ""
                self.location_descriptions.append(LocationDescription(index=idx, name=name, description=desc))
        else:
            # single flat location like [0, 'Entrance', 'desc']
            idx = response[0] if len(response) > 0 else 0
            name = response[1] if len(response) > 1 else ""
            desc = response[2] if len(response) > 2 else ""
            self.location_descriptions.append(LocationDescription(index=idx, name=name, description=desc))
        self.valid = len(self.location_descriptions) > 0
            
        
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