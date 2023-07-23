import random

from tale.base import Location, Exit, Door, Key, Living, ParseResult
from tale.errors import StoryCompleted
from tale.lang import capital
from tale.player import Player
from tale.util import Context, call_periodically
from tale.verbdefs import AGGRESSIVE_VERBS
from npcs.llama import *



main_hall = Location("Main Hall", "An area full of tables with people eating, drinking and talking")
bar = Location("Bar", "A bar carved from a single, massive tree trunk stretches across the room")
kitchen = Location("Kitchen", "The walls are lined with barrels and smoke is surrounding the steaming pots on the fires.")
hearth = Location("Hearth", "A place for newly arrived visitors to unthaw their frozen limbs.")
entrance = Location("Entrance", "A room full of furry and snow-covered coats. Loud voices and roars of laughter can be heard from the main hall.")
outside = Location("Outside", "A snow-storm is raging across the craggy landscape outside, it's dark, and noone to be seen. It's better to stay indoors")

#library_door = Door(["school_grounds", "door"], school_grounds, "A door leading to the school grounds", "", locked=False, opened=True, key_code="1")

Exit.connect(main_hall, ["bar", "north"], "", "To the north you are you see some people sitting over by a massive bar.", bar, ["main hall", "south"], "To the south you see an area full of tables with people eating, drinking and talking", "")

Exit.connect(main_hall, ["hearth", "west"], "To the west you see a giant hearth with a comforting fire", "", hearth, ["main hall", "east"], "To the east you see an area full of tables with people eating, drinking and talking", "")

Exit.connect(bar, ["kitchen", "north"], "", "To the north, there's a door leading to the kitchen.", kitchen, ["bar", "south"], "Through a door to the south you see the bar, and beyond that, the main hall", "")

Exit.connect(main_hall, ["entrance", "south"], "", "The entrance to the building is to the south.", entrance, ["main hall", "north"], "There's a warm glow and loud, noisy conversations coming through a doorway to the north", "")

Exit.connect(entrance, ["outside", "south"], "", "A biting wind reaches you through the door to the south.", outside, ["entrance", "north"], "There's shelter from the cold wind through a door to the north.", "")

main_hall.init_inventory([shanda, elid_gald])

bar.init_inventory([urta, norhardt])

hearth.init_inventory([count_karta])


