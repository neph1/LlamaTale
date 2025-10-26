
from copy import deepcopy
import json
import random
from typing import Any, Tuple
from tale import load_items, parse_utils, races
from tale import zone
from tale.base import Location
from tale.coord import Coord
from tale.llm import llm_config
from tale.llm.contexts.DungeonLocationsContext import DungeonLocationsContext
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext
from tale.llm.dynamic_story import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.llm.requests.generate_zone import GenerateZone
from tale.llm.requests.start_location import StartLocation
from tale.llm.responses.LocationDescriptionResponse import LocationDescriptionResponse
from tale.llm.responses.LocationResponse import LocationResponse
from tale.llm.responses.WorldCreaturesResponse import WorldCreaturesResponse
from tale.llm.responses.WorldItemsResponse import WorldItemsResponse
from tale.mob_spawner import MobSpawner
from tale.zone import Zone


class WorldBuilding():

    def __init__(self, io_util: IoUtil, default_body: dict, backend: str = 'kobold_cpp', json_grammar_key: str = ''):
        self.story_background_prompt = llm_config.params['STORY_BACKGROUND_PROMPT'] # Type: str
        self.backend = backend
        self.io_util = io_util
        self.default_body = default_body
        self.json_grammar = llm_config.params['JSON_GRAMMAR'] # Type: str
        self.json_grammar_key = json_grammar_key # Type: str
     
        self.item_types = llm_config.params['ITEM_TYPES'] # Type: list


    def build_location(self, location: Location, 
                       exit_location_name: str, 
                       zone_info: dict, 
                       context: WorldGenerationContext,
                       world_items: dict = {}, 
                       world_creatures: dict = {},
                       neighbors: dict = {}) -> Tuple[LocationResponse, MobSpawner]:
        """ Build 'up' a previously generated location.
            Returns lists of new locations, exits, and npcs."""
        
        spawn_prompt = ''
        spawn_chance = 0.35
        spawn = random.random() < spawn_chance
        if spawn:
            mood = zone_info.get('mood', 0)
            if isinstance(mood, str):
                num_mood = parse_utils.mood_string_to_int(mood)
            else:
                num_mood = mood
            num_mood = (int) (random.gauss(num_mood, 2))
            level = (int) (random.gauss(zone_info.get('level', 1), 2))
            mood_string = parse_utils.mood_string_from_int(num_mood)
            spawn_prompt = llm_config.params['SPAWN_PROMPT'].format(alignment=mood_string, level=level)

        items_prompt = ''
        item_amount = (int) (random.gauss(1, 2))
        if item_amount > 0:
            items_prompt = llm_config.params['ITEMS_PROMPT'].format(items=item_amount)

        prompt = llm_config.params['PRE_JSON_PROMPT']
        prompt += llm_config.params['CREATE_LOCATION_PROMPT'].format(
            context = '{context}',
            zone_info=zone_info,
            exit_locations=exit_location_name,
            location_name=location.name,
            spawn_prompt=spawn_prompt,
            items_prompt=items_prompt,
            exit_location_name=exit_location_name,
            exit_template=llm_config.params['EXIT_TEMPLATE'],
            npc_template=llm_config.params['NPC_TEMPLATE'],
            location_template=llm_config.params['LOCATION_TEMPLATE'])
            

        request_body = deepcopy(self.default_body)
        request_body['grammar'] = self.json_grammar
        result = self.io_util.synchronous_request(request_body, prompt=prompt, context=context.to_prompt_string())
        try:
            json_result = json.loads(parse_utils.sanitize_json(result))
            result = LocationResponse(json_result, location=location, exit_location_name=exit_location_name, world_items=world_items, world_creatures=world_creatures, neighbors=neighbors, item_types=self.item_types)
            spawner = None
            if result.npcs and world_creatures:
                spawner = self._try_generate_spawner(location, result.npcs, world_creatures)
            return result, spawner
        except json.JSONDecodeError as exc:
            print(exc)
            return LocationResponse.empty(), None
        except Exception as exc:
            print(exc)
            return LocationResponse.empty(), None
      
    def get_neighbor_or_generate_zone(self, current_zone: Zone, current_location: Location, target_location: Location, story: DynamicStory) -> Zone:
        """ Check if the target location is on the edge of the current zone. If not, will return the current zone.
        If it is, will check if there is a neighbor zone in the direction of the target location. If not, will
        generate a new zone in that direction."""

        direction = target_location.world_location.subtract(current_location.world_location)
        on_edge = current_zone.on_edge(current_location.world_location, direction)
        if on_edge:
            neighbor = current_zone.get_neighbor(direction)
            if neighbor:
                return neighbor
            else:
                world_generation_context = WorldGenerationContext(story_context=story.config.context, story_type=story.config.type, world_mood=story.config.world_mood, world_info=story.config.world_info)
                for i in range(5):
                    json_result = self._generate_zone(location_desc=target_location.description,
                                        context=world_generation_context,
                                        exit_location_name=current_location.name, 
                                        current_zone_info=current_zone.get_info(),
                                        direction=parse_utils.direction_from_coordinates(direction))  # type: dict
                    if json_result:
                        zone = self.validate_zone(json_result, 
                                                  current_location.world_location.add(
                                                      direction.multiply(json_result.get('size', current_zone.size_z if direction.z != 0 else current_zone.size))))
                        if zone and story.add_zone(zone):
                            zone.level = (zone.level + 1) if random.random() < 0.5 else zone.level
                            return zone
        return current_zone

        
    def _generate_zone(self, location_desc: str, context: WorldGenerationContext, exit_location_name: str = '', current_zone_info: dict = {}, direction: str = '', catalogue: dict = {}) -> dict:
        """ Generate a zone based on the current story context"""
        prompt = GenerateZone().build_prompt({
            'direction': direction,
            'current_zone_info': current_zone_info,
            'exit_location_name': exit_location_name,
            'location_desc': location_desc,
            'world_mood': context.world_mood,
            'catalogue': catalogue,
        })
        
        request_body = deepcopy(self.default_body)
        result = self.io_util.synchronous_request(request_body, prompt=prompt, context=context.to_prompt_string())
        try:
            return json.loads(parse_utils.sanitize_json(result))
        except json.JSONDecodeError as exc:
            print(exc)
            return None

    def validate_zone(self, json_result: dict, center: Coord) -> Zone:
        """Create the Zone object."""
        zone = Zone(name=json_result['name'], description=json_result['description'])
        zone.level = json_result.get('level', 1)
        zone.mood = json_result.get('mood', 0)
        zone.center = center
        zone.size = json_result.get('size', 5)
        zone.races = json_result.get('races', [])
        zone.items = json_result.get('items', [])
        return zone
    
    def generate_start_location(self, location: Location, zone_info: dict, context: WorldGenerationContext, world_items: dict = {}) -> LocationResponse:
        """ Generate a location based on the current story context
        One gotcha is that the location is not returned, its contents are just updated"""

        prompt = StartLocation().build_prompt({
            'zone_info': zone_info,
            'location': location,
            'story_type': context.story_type,
            'world_info': context.world_info,
            'story_context': context.story_context,
        })
        
        request_body = deepcopy(self.default_body)
        if self.json_grammar_key:
            request_body[self.json_grammar_key] = self.json_grammar
        result = self.io_util.synchronous_request(request_body, prompt=prompt)
        if not result:
            return LocationResponse.empty()
        try:
            json_result = json.loads(parse_utils.sanitize_json(result))
            if not json_result.get('name', None):
                return LocationResponse.empty()
            location.name=json_result['name']
            return LocationResponse(json_result=json_result, location=location, exit_location_name='', item_types=self.item_types, world_items=world_items)
        except Exception as exc:
            print(exc.with_traceback())
            return LocationResponse.empty()
        
    def generate_start_zone(self, location_desc: str, context: WorldGenerationContext) -> Zone:
        """ Generate a zone based on the current story context"""

        prompt = llm_config.params['PRE_JSON_PROMPT']
        prompt += llm_config.params['CREATE_ZONE_PROMPT'] .format(
            context = '{context}',
            direction='',
            zone_info='',
            exit_location='',
            location_desc=location_desc,
            zone_template=llm_config.params['ZONE_TEMPLATE'])
        
        request_body = deepcopy(self.default_body)
        if self.json_grammar_key:
            request_body[self.json_grammar_key] = self.json_grammar
        result = self.io_util.synchronous_request(request_body, prompt=prompt, context=context.to_prompt_string())
        try:
            json_result = json.loads(parse_utils.sanitize_json(result))
            return zone.from_json(json_result)
        except json.JSONDecodeError as exc:
            print(f'Error generating zone: {exc}')
            return None
        

    def generate_world_items(self, world_generation_context: WorldGenerationContext, item_types: list = [], count: int = 7) -> WorldItemsResponse:
        """Generate world items one at a time to avoid large JSON arrays and token limits.
        
        Args:
            world_generation_context: Context for world generation
            item_types: List of valid item types
            count: Number of items to generate (default 7)
            
        Returns:
            WorldItemsResponse containing the generated items
        """
        items = []
        previously_generated_names = []
        
        for i in range(count):
            # Build prompt with previously generated items to avoid repetition
            previously_generated = ""
            if previously_generated_names:
                previously_generated = f"Previously generated items: {', '.join(previously_generated_names)}. Ensure this item is different. "
            
            prompt = llm_config.params['WORLD_ITEM_SINGLE'].format(
                context = '{context}',
                item_template=llm_config.params['ITEM_TEMPLATE'],
                item_types=item_types or self.item_types,
                previously_generated=previously_generated)
            
            request_body = deepcopy(self.default_body)
            if self.json_grammar_key:
                request_body[self.json_grammar_key] = self.json_grammar

            result = self.io_util.synchronous_request(request_body, prompt=prompt, context=world_generation_context.to_prompt_string())
            try:
                json_result = json.loads(parse_utils.sanitize_json(result))
                if 'item' in json_result and json_result['item']:
                    item = json_result['item']
                    items.append(item)
                    if 'name' in item:
                        previously_generated_names.append(item['name'])
            except json.JSONDecodeError as exc:
                print(f'Error generating item {i+1}/{count}: {exc}')
                # Continue to next item instead of failing completely
                continue
        
        return WorldItemsResponse({'items': items})
    
    def generate_world_creatures(self, world_generation_context: WorldGenerationContext, count: int = 5) -> WorldCreaturesResponse:
        """Generate world creatures one at a time to avoid large JSON arrays and token limits.
        
        Args:
            world_generation_context: Context for world generation
            count: Number of creatures to generate (default 5)
            
        Returns:
            WorldCreaturesResponse containing the generated creatures
        """
        creatures = []
        previously_generated_names = []
        
        for i in range(count):
            # Build prompt with previously generated creatures to avoid repetition
            previously_generated = ""
            if previously_generated_names:
                previously_generated = f"Previously generated creatures: {', '.join(previously_generated_names)}. Ensure this creature is different. "
            
            prompt = llm_config.params['WORLD_CREATURE_SINGLE'].format(
                context = '{context}',
                creature_template=llm_config.params['CREATURE_TEMPLATE'],
                previously_generated=previously_generated)
            
            request_body = deepcopy(self.default_body)
            if self.json_grammar_key:
                request_body[self.json_grammar_key] = self.json_grammar

            result = self.io_util.synchronous_request(request_body, prompt=prompt, context=world_generation_context.to_prompt_string())
            try:
                json_result = json.loads(parse_utils.sanitize_json(result))
                if 'creature' in json_result and json_result['creature']:
                    creature = json_result['creature']
                    creatures.append(creature)
                    if 'name' in creature:
                        previously_generated_names.append(creature['name'])
            except json.JSONDecodeError as exc:
                print(f'Error generating creature {i+1}/{count}: {exc}')
                # Continue to next creature instead of failing completely
                continue
        
        return WorldCreaturesResponse({'creatures': creatures})
    
    def generate_random_spawn(self, location: Location, context: WorldGenerationContext, zone_info: dict, world_creatures: list, world_items: list) -> bool:
        location_info = {'name': location.title, 'description': location.look(short=True), 'exits': location.exits}
        prompt = llm_config.params['PLAYER_ENTER_PROMPT'].format(context = '{context}',
                                                npc_template=llm_config.params['NPC_TEMPLATE'],
                                                zone_info=zone_info,
                                                location_info=location_info)
        request_body = deepcopy(self.default_body)
        if self.json_grammar_key:
            request_body[self.json_grammar_key] = self.json_grammar
        
        result = self.io_util.synchronous_request(request_body, prompt=prompt, context=context.to_prompt_string())
        try:
            json_result = json.loads(parse_utils.sanitize_json(result))
            creatures = json_result["npcs"]
            creatures.extend(json_result["mobs"])
            creatures = parse_utils.replace_creature_with_world_creature(creatures, world_creatures)
            creatures = parse_utils.load_npcs(creatures, world_items = world_items, parse_occupation=True)
            for c in creatures.values():
                location.insert(c)
            items = json_result["items"]
            items = parse_utils.replace_items_with_world_items(items, world_items)
            items = load_items.load_items(items)
            for i in items.values():
                location.insert(i)
            return True
        except Exception as exc:
            print(exc)
            return False
        
    def generate_note_lore(self, context: WorldGenerationContext, zone_info: str) -> str:
        """ Generate a note with story lore."""
        prompt = llm_config.params['NOTE_LORE_PROMPT'].format(context = '{context}',
                                                zone_info=zone_info)
        request_body = deepcopy(self.default_body)
        result = self.io_util.synchronous_request(request_body, prompt=prompt, context=context.to_prompt_string())
        try:
            return parse_utils.trim_response(result)
        except Exception as exc:
            print(exc)
            return None
        
    def generate_dungeon_locations(self, context: DungeonLocationsContext) -> LocationDescriptionResponse:
        """ Generate a list of descriptins for locations in a dungeon."""
        prompt = llm_config.params['CREATE_DUNGEON_LOCATIONS'].format(context = context.to_prompt_string(), dungeon_location_template=llm_config.params['DUNGEON_LOCATION_TEMPLATE'])
        request_body = deepcopy(self.default_body)
        if self.json_grammar_key:
            request_body[self.json_grammar_key] = self.json_grammar
        result = self.io_util.synchronous_request(request_body, prompt=prompt, context=context.to_prompt_string())
        try:
            parsed = json.loads(parse_utils.sanitize_json(result))
            return LocationDescriptionResponse(parsed)
        except json.JSONDecodeError as exc:
            print(exc)
            return LocationDescriptionResponse([])

    def _validate_creatures(self, creatures: dict) -> dict:
        new_creatures = {}
        for creature in creatures:
            if not creature.get("name", ""):
                continue
            creature["name"] = creature["name"].lower()
            if creature.get("unarmed_attack", ""):
                try:
                    creature["unarmed_attack"] = races.UnarmedAttack[creature["unarmed_attack"]]
                except:
                    creature["unarmed_attack"] = races.UnarmedAttack.BITE
            else:
                creature["unarmed_attack"] = races.UnarmedAttack.BITE
            level = creature.get("level", 1)
            if level < 1:
                creature["level"] = 1
            creature["type"] = "Mob"
            new_creatures[creature["name"]] = creature
        return new_creatures
    
    def _try_generate_spawner(self, location: Location, npcs: list, world_creatures: list):
        for npc in npcs:
            for world_creature in world_creatures:
                if npc.name == world_creature['name'].lower():
                    mob_spawner = MobSpawner(npc, location, 30, 2)
                    return mob_spawner
