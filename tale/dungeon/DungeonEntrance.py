from tale.base import Exit
from tale.coord import Coord
from tale.dungeon.dungeon import Dungeon
from tale.dungeon.dungeon_config import DungeonConfig
from tale.dungeon.dungeon_generator import ItemPopulator, LayoutGenerator, MobPopulator
from tale.llm.dynamic_story import DynamicStory
from tale.zone import Zone


class DungeonEntrance(Exit):
    """
    A special exit that leads to a dungeon.

    This can be added to any normal location to provide access to a dungeon.
    """

    def build_dungeon(self, story: 'DynamicStory', llm_util, config: DungeonConfig = None) -> Dungeon:
        """
        Build the dungeon if not already built.
        
        Args:
            story: The story this dungeon belongs to
            llm_util: LLM utility for generating descriptions
            config: DungeonConfig defining the dungeon properties (optional)
        """
        # Use provided config or create default
        if config is None:
            config = DungeonConfig(
                name=self.short_description if hasattr(self, 'short_description') else "Dungeon",
                description="A dark dungeon",
                races=["bat", "wolf"],
                items=["torch"],
                max_depth=3
            )

        # Create the dungeon
        self.dungeon = Dungeon(
            name=config.name,
            story=story,
            llm_util=llm_util,
            layout_generator=LayoutGenerator(),
            mob_populator=MobPopulator(),
            item_populator=ItemPopulator(),
            max_depth=config.max_depth
        )
        
        # Create the first zone for the dungeon
        zone = Zone(f"{config.name}_level_0", f"Level 0 of {config.name}")
        zone.level = 1
        zone.center = Coord(0, 0, 0)
        
        # Set creatures and items from config
        zone.races = config.races
        zone.items = config.items
        
        # Store the dungeon config in the zone
        zone.dungeon_config = config

        # Add zone to story
        self.dungeon.story.add_zone(zone)

        # Generate the first level
        self.dungeon.generate_level(zone, depth=0)

        # Get the entrance location and update the target
        self.target = self.dungeon.get_entrance_location()

        return self.dungeon