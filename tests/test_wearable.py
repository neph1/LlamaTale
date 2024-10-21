

from tale.races import BodyType
from tale.wearable import WearLocation, body_parts_for_bodytype, load_wearables_from_json, random_wearable_for_body_part

class TestLoadWearablesFromJson:

    def test_load_wearables_from_json(self):
        wearables = load_wearables_from_json('../items/wearables_fantasy.json')
        assert wearables

    def test_load_wearables_from_json_modern(self):
        wearables = load_wearables_from_json('../items/wearables_modern.json')
        assert wearables
class TestBodyPartsForBodyType:

    def test_body_parts_for_humanoid(self):
        bodyParts = body_parts_for_bodytype(BodyType.HUMANOID)
        assert bodyParts == list(WearLocation)[1:-3]

    def test_body_parts_for_quadruped(self):
        bodyParts = body_parts_for_bodytype(BodyType.QUADRUPED)
        assert bodyParts == [WearLocation.HEAD, WearLocation.LEGS, WearLocation.TORSO, WearLocation.FEET, WearLocation.NECK]

    def test_body_parts_for_winged_man(self):
        bodyParts = body_parts_for_bodytype(BodyType.WINGED_MAN)
        assert bodyParts == list(WearLocation)[1:-3]

    def test_body_parts_for_tentacled(self):
        bodyParts = body_parts_for_bodytype(BodyType.TENTACLED)
        assert bodyParts == None

class TestRandomWearableForBodyPart:

    def test_wearable_for_head(self):
        wearable = random_wearable_for_body_part(WearLocation.HEAD, setting='fantasy')
        assert wearable['location'] == WearLocation.HEAD

    def test_wearable_for_torso(self):
        wearable = random_wearable_for_body_part(WearLocation.TORSO, setting='fantasy')
        assert wearable['location'] == WearLocation.TORSO

    def test_wearable_armor_only(self):
        wearable = random_wearable_for_body_part(WearLocation.TORSO, setting='fantasy', armor_only=True)
        assert wearable
        assert wearable['ac'] > 0

    def test_wearable_for_modern_setting(self):
        wearable = random_wearable_for_body_part(WearLocation.HEAD, setting='modern')
        assert wearable
        assert wearable['location'] == WearLocation.HEAD
