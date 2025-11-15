from tale.base import Exit
from tale.coord import Coord
from tale.dungeon.dungeon import Dungeon
from tale.dungeon.dungeon_generator import ItemPopulator, LayoutGenerator, MobPopulator
from tale.llm.dynamic_story import DynamicStory
from tale.zone import Zone


class DungeonEntrance(Exit):
    """
    A special exit that leads to a dungeon.

    This can be added to any normal location to provide access to a dungeon.
    """

    def build_dungeon(self, story: 'DynamicStory', llm_util) -> Dungeon:
        """
        Build the dungeon if not already built.
        """

        # Create the first zone for the dungeon
        self.dungeon = Dungeon(
        name=self.short_description,
        story=story,
        llm_util=llm_util,
        layout_generator=LayoutGenerator(),
        mob_populator=MobPopulator(),
        item_populator=ItemPopulator(),
        max_depth=3
        )
                # Create the first zone for the dungeon
        zone = Zone(f"{self.name}_level_0", f"Level 0 of {self.name}")
        zone.level = 1
        zone.center = Coord(0, 0, 0)
        # Set default creatures and items for the dungeon
        zone.races = ["bat", "wolf"]
        zone.items = ["torch"]

        # Add zone to story
        self.dungeon.story.add_zone(zone)

        # Generate the first level
        self.dungeon.generate_level(zone, depth=0)

        # Get the entrance location and update the target
        self.target = self.dungeon.get_entrance_location()

        return self.dungeon