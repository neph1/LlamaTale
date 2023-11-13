""" This contains various generic items the LLM can use when it want to add some
    Should be dicts after a refactor...
"""


from tale.base import Weapon
from tale.weapon_type import WeaponType

generic_weapons = [
     Weapon(name="Dagger", weapon_type=WeaponType.ONE_HANDED, short_descr='A steel dagger', base_damage=1).to_dict(),
     Weapon(name="Club", weapon_type=WeaponType.ONE_HANDED, short_descr='A wooden club', base_damage=1).to_dict(),
]

fantasy_weapons = [
    Weapon(name="Sword", weapon_type=WeaponType.ONE_HANDED, short_descr='A plain sword', base_damage=2).to_dict(),
    Weapon(name="Spear", weapon_type=WeaponType.TWO_HANDED, short_descr='A spear', base_damage=3).to_dict(),
    Weapon(name='Crossbow', weapon_type=WeaponType.TWO_HANDED_RANGED, short_descr='A simple crossbow', base_damage=2).to_dict(),
]

modern_weapons = [
    Weapon(name="Rusty pipe", weapon_type=WeaponType.ONE_HANDED, short_descr='A left-over piece of plumbing', base_damage=1).to_dict(),
    Weapon(name='Semi-automatic pistol', weapon_type=WeaponType.ONE_HANDED_RANGED, short_descr='A pistol that has seen better days.', base_damage=2).to_dict(),
]


generic_items = {
    'fantasy': [*generic_weapons, *fantasy_weapons],
    'modern': [*generic_weapons, *modern_weapons],
    'postapoc': [*generic_weapons, *modern_weapons],
    '': generic_weapons,
}

