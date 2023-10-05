""" This contains various generic items the LLM can use when it want to add some"""


from tale.base import Weapon
from tale.weapon_type import WeaponType

generic_weapons = {
    'dagger': Weapon(name="Dagger", weapon_type=WeaponType.ONE_HANDED, short_descr='A steel dagger', base_damage=1),
    'club': Weapon(name="Club", weapon_type=WeaponType.ONE_HANDED, short_descr='A wooden club', base_damage=1),
}

fantasy_weapons = {
    'sword': Weapon(name="Sword", weapon_type=WeaponType.ONE_HANDED, short_descr='A plain sword', base_damage=2),
    'spear': Weapon(name="Spear", weapon_type=WeaponType.TWO_HANDED, short_descr='A spear', base_damage=3),
    'crossbow': Weapon(name='Crossbow', weapon_type=WeaponType.TWO_HANDED_RANGED, short_descr='A simple crossbow', base_damage=2),
}

modern_weapons = {

}


generic_items = {
    'fantasy': {**generic_weapons, **fantasy_weapons},
    'modern': {**generic_weapons, **modern_weapons},
}