

from tale import parse_utils
from tale.base import Location


class LocationResponse():

    def __init__(self, json_result: dict, 
                    location: Location,
                    exit_location_name: str, 
                    world_items: dict = {}, 
                    world_creatures: dict = {},
                    neighbors: dict = {},
                    item_types: dict = {}):
        
        
        self.new_locations = []
        self.exits = []
        self.npcs = []
        if not json_result:
            self.valid = False
            return
        if json_result.get('name', None):
            location.name=json_result['name']
        self.item_types = item_types
        self.valid = self._validate_location(json_result, 
                                            location, 
                                            exit_location_name=exit_location_name, 
                                            world_items=world_items, 
                                            world_creatures=world_creatures,
                                            neighbors=neighbors)

    def _validate_location(self, json_result: dict, 
                           location_to_build: Location, 
                           exit_location_name: str, 
                           world_items: dict = {}, 
                           world_creatures: dict = {},
                           neighbors: dict = {}):
        """Validate the location generated by LLM and update the location object."""
        try:
            # start locations have description already, and we don't want to overwrite it
            if not location_to_build.description:
                description = json_result.get('description', '')
                if not description:
                    if not json_result.get('exits'):
                        # this is a hack to get around that it sometimes generates an extra json layer
                        json_result = json_result[location_to_build.name]
                    else:
                        # some models don't generate description, sometimes
                        json_result['description'] = exit_location_name
                location_to_build.description = json_result['description']
                
            
            self._add_items(location_to_build, json_result, world_items)

            self.npcs = self._add_npcs(location_to_build, json_result, world_creatures).values()


            new_locations, exits = parse_utils.parse_generated_exits(json_result.get('exits', []), 
                                                                     exit_location_name, 
                                                                     location_to_build)
            location_to_build.built = True
            self.new_locations = new_locations
            self.exits = exits
            return True
        except Exception as exc:
            print(f'Exception while parsing location {json_result} ')
            print(exc.with_traceback())
            return False
        
              
    def _add_items(self, location: Location, json_result: dict, world_items: dict = {}):
        generated_items = json_result.get("items", [])
        if not generated_items:
            return location
        
        if world_items:
            generated_items = parse_utils.replace_items_with_world_items(generated_items, world_items)
        # the loading function works differently and will not insert the items into the location
        # since the item doesn't have the location
        items = self._validate_items(generated_items)
        items = parse_utils.load_items(items)
        for item in items.values():
            location.insert(item, None)
        return location
    
    def _add_npcs(self, location: Location, json_result: dict, world_creatures: dict = {}) -> dict:
        generated_npcs = json_result.get("npcs", [])
        if not generated_npcs:
            return {}
        if world_creatures:
            generated_npcs = parse_utils.replace_creature_with_world_creature(generated_npcs, world_creatures)
        try:
            generated_npcs = parse_utils.load_npcs(generated_npcs)
            for npc in generated_npcs.values():
                location.insert(npc, None)
        except Exception as exc:
            print(exc)
        return generated_npcs
    

    def _validate_items(self, items: dict) -> list:
        new_items = []
        for item in items:
            if isinstance(item, str):
                # TODO: decide what to do with later
                new_items.append({"name":item, "type":"Other"})
                continue
            if not item.get("name", ""):
                continue
            item["name"] = item["name"].lower()
            type = item.get("type", "Other")
            if type not in self.item_types:
                item["type"] = "Other"
            new_items.append(item)
        return new_items

    @classmethod
    def empty(self):
        return LocationResponse(json_result={}, location=None, exit_location_name='')



    