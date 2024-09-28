from tale.skills.magic import MagicSkills, MagicType


class TestMagicSkills():

    def test_to_json(self):
        skills = MagicSkills()
        skills.set(MagicType.HEAL, 5)
        skills.set(MagicType.BOLT, 3)
        skills.set(MagicType.DRAIN, 1)
        
        expected_json = {
            MagicType.HEAL: 5,
            MagicType.BOLT: 3,
            MagicType.DRAIN: 1
        }

        assert skills.to_json() == expected_json

    def test_from_json(self):
        json_data = {
            MagicType.HEAL: 5,
            MagicType.BOLT: 3,
            MagicType.DRAIN: 1
        }

        expected_skills = MagicSkills()
        expected_skills.set(MagicType.HEAL, 5)
        expected_skills.set(MagicType.BOLT, 3)
        expected_skills.set(MagicType.DRAIN, 1)

        assert MagicSkills.from_json(json_data) == expected_skills