"""Zone for the agent sandbox: a garden with an autonomous agent NPC,
a villager to talk to, a hostile rat, and items to pick up / wield / eat /
give / use a key on. A locked door leads to the shed (for pick_lock)."""

from tale.base import Door, Exit, Key, Location, Wearable, Weapon
from tale.items.basic import Drink, Food
from tale.llm.LivingNpc import LivingNpc
from tale.npc_defs import StationaryMob, StationaryNpc
from tale.skills.weapon_type import WeaponType
from tale.util import Context, call_periodically
from tale.wearable import WearLocation


class Agent(StationaryNpc):
    """An autonomous NPC: plans and performs its own actions via the LLM,
    even when no player is around."""

    @call_periodically(5, 10)
    def do_idle_action(self, ctx: Context) -> None:
        if not self.location or self.location.name == 'Limbo':
            return
        self.idle_action()


garden = Location("garden", "A small fenced vegetable garden with neat rows of herbs and vegetables. A well stands in the middle.")
cottage = Location("cottage", "A cozy one-room cottage with a fireplace, a table and a bed.")
shed = Location("shed", "A dusty old toolshed full of rakes, pots and mouse droppings.")

Exit.connect(garden, ["cottage", "north"], "A wooden door leads north into the cottage.", "",
             cottage, ["garden", "south"], "The garden lies to the south.", "")
Door.connect(garden, ["shed", "east"], "A heavy oak door leads east into the shed.", "",
             shed, ["garden", "west"], "The garden is to the west.", "",
             locked=True, key_code="shed_key")

# the autonomous agent
bram = Agent("bram", "m", title="Bram",
             descr="A wiry young gardener with soil under his fingernails and a mind of his own.",
             short_descr="a wiry young gardener", age=28,
             personality="curious, industrious, a bit reckless", occupation="gardener",
             race="human", parse_occupation=True)
bram.autonomous = True
bram.output_thoughts = True
bram.goal = "Keep the garden tidy and free of rats."
bram.example_voice = "Bram says: \"Oi! Mind the tomatoes!\""

# a non-autonomous NPC to talk to / react to the agent
mira = LivingNpc("mira", "f", title="Mira",
                 descr="A cheerful villager watering her flowers.",
                 short_descr="a cheerful villager", age=41,
                 personality="friendly, gossipy, easily startled", occupation="villager",
                 race="human", parse_occupation=True)

# something to fight
rat = StationaryMob("giant rat", "m", title="giant rat",
                    descr="A vicious giant rat the size of a cat, rooting around the compost heap.",
                    short_descr="a vicious giant rat", race="giant rat")
rat.aggressive = True

# things to interact with
sword = Weapon("rusty sword", weapon_type=WeaponType.ONE_HANDED, base_damage=3,
               short_descr="a rusty sword", descr="An old rusty sword. Better than bare hands.")
apple = Food(name="apple", short_descr="a crisp apple", descr="A crisp red apple, freshly picked.", value=1)
ale = Drink(name="ale", short_descr="a jug of ale", descr="A stone jug of strong-smelling ale.", value=2)
sun_hat = Wearable("sun hat", wear_location=WearLocation.HEAD,
                   short_descr="a wide-brimmed sun hat", descr="A wide-brimmed straw hat against the sun.")
shed_key = Key(name="shed key", short_descr="a small brass key", descr="A small brass key, labelled 'shed'.")
shed_key.key_for(code="shed_key")

bram.init_inventory([apple, sword])  # so the agent can give / wield things
garden.init_inventory([bram, mira, rat])
garden.insert(sun_hat, None)
garden.insert(ale, None)
garden.insert(shed_key, None)

all_locations = [garden, cottage, shed]
