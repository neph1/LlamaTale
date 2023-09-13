

from enum import Enum


class WeaponType(Enum):

    ONE_HANDED = 1
    TWO_HANDED = 2
    ONE_HANDED_RANGED = 3
    TWO_HANDED_RANGED = 4
    MAGIC = 5
    UNARMED = 6
    THROWING = 7


ranged = [WeaponType.ONE_HANDED_RANGED, WeaponType.TWO_HANDED_RANGED, WeaponType.THROWING]

hand_to_hand = [WeaponType.UNARMED, WeaponType.ONE_HANDED, WeaponType.TWO_HANDED]