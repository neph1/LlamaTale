from tale.skills.skills import SkillType, Skills


class TestSkills():

    def test_to_json(self):
        skills = Skills()
        skills.set(SkillType.HIDE, 5)
        skills.set(SkillType.SEARCH, 3)
        skills.set(SkillType.PICK_LOCK, 1)
        skills.set(SkillType.DODGE, 2)
        skills.set(SkillType.SET_TRAP, 4)
        skills.set(SkillType.DISARM_TRAP, 6)

        expected_json = {
            SkillType.HIDE.value: 5,
            SkillType.SEARCH.value: 3,
            SkillType.PICK_LOCK.value: 1,
            SkillType.DODGE.value: 2,
            SkillType.SET_TRAP.value: 4,
            SkillType.DISARM_TRAP.value: 6
        }

        assert skills.to_json() == expected_json

    def test_from_json(self):
        json_data = {
            SkillType.HIDE.value: 5,
            SkillType.SEARCH.value: 3,
            SkillType.PICK_LOCK.value: 1,
            SkillType.DODGE.value: 2,
            SkillType.SET_TRAP.value: 4,
            SkillType.DISARM_TRAP.value: 6
        }

        expected_skills = Skills()
        expected_skills.set(SkillType.HIDE, 5)
        expected_skills.set(SkillType.SEARCH, 3)
        expected_skills.set(SkillType.PICK_LOCK, 1)
        expected_skills.set(SkillType.DODGE, 2)
        expected_skills.set(SkillType.SET_TRAP, 4)
        expected_skills.set(SkillType.DISARM_TRAP, 6)

        assert Skills.from_json(json_data) == expected_skills