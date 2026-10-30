from copy import deepcopy
import random
from typing import Tuple
from tale import load_items, parse_utils, races
from tale.base import Location
from tale.coord import Coord
from tale.llm import llm_config
from tale.llm.contexts.DungeonLocationsContext import DungeonLocationsContext
from tale.llm.contexts.WorldGenerationContext import WorldGenerationContext
from tale.llm.dynamic_story import DynamicStory
from tale.llm.llm_io import IoUtil
from tale.llm.requests.generate_dungeon_config import GenerateDungeonConfig
from tale.llm.requests.generate_zone import GenerateZone
from tale.llm.requests.start_location import StartLocation
from tale.llm.responses.LocationDescriptionResponse import LocationDescriptionResponse
from tale.llm.responses.LocationResponse import LocationResponse
from tale.llm.responses.WorldCreaturesResponse import WorldCreaturesResponse
from tale.llm.responses.WorldItemsResponse import WorldItemsResponse
from tale.llm.schemas import (
    DungeonConfigSchema,
    DungeonEntranceSchema,
    DungeonLocationsSchema,
    LocationSchema,
    SpawnSchema,
    WorldCreatureSchema,
    WorldItemSchema,
    ZoneSchema,
)
from tale.mob_spawner import MobSpawner
from tale.zone import Zone


class WorldBuilding():

    def __init__(self, io_util: IoUtil, default_body: dict, backend: str = 'kobold_cpp'):
        self.story_background_prompt = llm_config.params['STORY_BACKGROUND_PROMPT']
        self.backend = backend
        self.io_util = io_util
        self.default_body = default_body

        self.item_types = llm_config.params['ITEM_TYPES']


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

        prompt = llm_config.params['CREATE_LOCATION_PROMPT'].format(
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
        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=LocationSchema, context=context.to_prompt_string())
            result = LocationResponse(model, location=location, exit_location_name=exit_location_name, world_items=world_items, world_creatures=world_creatures, neighbors=neighbors, item_types=self.item_types)
            spawner = None
            if result.npcs and world_creatures:
                spawner = self._try_generate_spawner(location, result.npcs, world_creatures)
            return result, spawner
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
                    zone_model = self._generate_zone(location_desc=target_location.description,
                                        context=world_generation_context,
                                        exit_location_name=current_location.name,
                                        current_zone_info=current_zone.get_info(),
                                        direction=parse_utils.direction_from_coordinates(direction))
                    if zone_model:
                        zone = self.validate_zone(zone_model,
                                                  current_location.world_location.add(
                                                      direction.multiply(zone_model.size if direction.z != 0 else zone_model.size)))
                        if zone:
                            # route the zone addition through the story
                            # modification layer so the LLM path shares one
                            # surface with MCP (fall back to the story if no
                            # manager is registered, e.g. in tests)
                            from tale import story_manager
                            try:
                                added = story_manager.current().add_zone_object(zone)
                            except RuntimeError:
                                added = story.add_zone(zone)
                            if added:
                                zone.level = (zone.level + 1) if random.random() < 0.5 else zone.level
                                if random.random() < 0.25:
                                    dungeon_config = self._generate_dungeon_config(zone, world_generation_context)
                                    if dungeon_config:
                                        zone.dungeon_config = dungeon_config
                                return zone
        return current_zone


    def _generate_zone(self, location_desc: str, context: WorldGenerationContext, exit_location_name: str = '', current_zone_info: dict = {}, direction: str = '', catalogue: dict = {}) -> ZoneSchema:
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
        try:
            return self.io_util.structured_request(request_body, prompt=prompt, model=ZoneSchema, context=context.to_prompt_string())
        except Exception as exc:
            print(exc)
            return None

    def _generate_dungeon_config(self, zone: Zone, context: WorldGenerationContext):
        """Generate a dungeon config for the given zone."""
        from tale.dungeon.dungeon_config import DungeonConfig

        prompt = GenerateDungeonConfig().build_prompt({
            'zone_info': zone.get_info(),
        })

        request_body = deepcopy(self.default_body)
        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=DungeonConfigSchema, context=context.to_prompt_string())
            return DungeonConfig.from_json(model.model_dump())
        except Exception as exc:
            print(f'Error generating dungeon config: {exc}')
            return None

    def validate_zone(self, model: ZoneSchema, center: Coord) -> Zone:
        """Create the Zone object."""
        zone = Zone(name=model.name, description=model.description)
        zone.level = model.level
        zone.mood = model.mood
        zone.center = center
        zone.size = model.size
        zone.races = model.races
        zone.items = model.items
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
        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=LocationSchema)
            if not model.name:
                return LocationResponse.empty()
            location.name = model.name
            return LocationResponse(model=model, location=location, exit_location_name='', item_types=self.item_types, world_items=world_items)
        except Exception as exc:
            print(exc)
            return LocationResponse.empty()

    def generate_start_zone(self, location_desc: str, context: WorldGenerationContext) -> Zone:
        """ Generate a zone based on the current story context"""

        prompt = llm_config.params['CREATE_ZONE_PROMPT'].format(
            context = '{context}',
            direction='',
            zone_info='',
            exit_location='',
            location_desc=location_desc,
            zone_template=llm_config.params['ZONE_TEMPLATE'])

        request_body = deepcopy(self.default_body)
        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=ZoneSchema, context=context.to_prompt_string())
            return Zone.from_json(model.model_dump())
        except Exception as exc:
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
            previously_generated = f"Previously generated items: {', '.join(previously_generated_names)}. Ensure this item is different. " if previously_generated_names else ""

            prompt = llm_config.params['WORLD_ITEM_SINGLE'].format(
                context = '{context}',
                item_template=llm_config.params['ITEM_TEMPLATE'],
                item_types=item_types or self.item_types,
                previously_generated=previously_generated)

            request_body = deepcopy(self.default_body)

            try:
                model = self.io_util.structured_request(request_body, prompt=prompt, model=WorldItemSchema, context=world_generation_context.to_prompt_string())
                if model.item:
                    items.append(model.item)
                    if model.item.name:
                        previously_generated_names.append(model.item.name)
            except Exception as exc:
                print(f'Error generating item {i+1}/{count}: {exc}')
                continue

        return WorldItemsResponse(items)

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
            previously_generated = f"Previously generated creatures: {', '.join(previously_generated_names)}. Ensure this creature is different. " if previously_generated_names else ""

            prompt = llm_config.params['WORLD_CREATURE_SINGLE'].format(
                context = '{context}',
                creature_template=llm_config.params['CREATURE_TEMPLATE'],
                previously_generated=previously_generated)
            request_body = deepcopy(self.default_body)

            try:
                model = self.io_util.structured_request(request_body, prompt=prompt, model=WorldCreatureSchema, context=world_generation_context.to_prompt_string())
                if model.creature:
                    creatures.append(model.creature)
                    if model.creature.name:
                        previously_generated_names.append(model.creature.name)
            except Exception as exc:
                print(f'Error generating creature {i+1}/{count}: {exc}')
                continue
        return WorldCreaturesResponse(creatures)

    def generate_random_spawn(self, location: Location, context: WorldGenerationContext, zone_info: dict, world_creatures: list, world_items: list) -> bool:
        location_info = {'name': location.title, 'description': location.look(short=True), 'exits': location.exits}
        prompt = llm_config.params['PLAYER_ENTER_PROMPT'].format(context = '{context}',
                                                npc_template=llm_config.params['NPC_TEMPLATE'],
                                                zone_info=zone_info,
                                                location_info=location_info)
        request_body = deepcopy(self.default_body)

        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=SpawnSchema, context=context.to_prompt_string())
            creatures = [n.model_dump() for n in model.npcs]
            creatures.extend(model.mobs)
            creatures = parse_utils.replace_creature_with_world_creature(creatures, world_creatures)
            creatures = parse_utils.load_npcs(creatures, world_items = world_items, parse_occupation=True)
            for c in creatures.values():
                location.insert(c)
            items = []
            for item in model.items:
                if isinstance(item, str):
                    items.append({'name': item, 'type': 'Other'})
                else:
                    items.append(item.model_dump())
            if world_items:
                items = parse_utils.replace_items_with_world_items(items, world_items)
            else:
                items = []
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
        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=DungeonLocationsSchema, context=context.to_prompt_string())
            return LocationDescriptionResponse(model)
        except Exception as exc:
            print(exc)
            return LocationDescriptionResponse(DungeonLocationsSchema(locations=[]))

    def generate_dungeon_entrance(self, location: Location, dungeon_config: dict, context: WorldGenerationContext) -> dict:
        """Generate a dungeon entrance that fits the location and dungeon config."""
        prompt = llm_config.params['CREATE_DUNGEON_ENTRANCE_PROMPT'].format(
            context='{context}',
            location_name=location.name,
            location_description=location.description,
            dungeon_config=dungeon_config,
            dungeon_entrance_template=llm_config.params['DUNGEON_ENTRANCE_TEMPLATE'])

        request_body = deepcopy(self.default_body)

        try:
            model = self.io_util.structured_request(request_body, prompt=prompt, model=DungeonEntranceSchema, context=context.to_prompt_string())
            return model.model_dump()
        except Exception as exc:
            print(f'Error generating dungeon entrance: {exc}')
            return None

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
