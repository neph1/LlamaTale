from tale.skills.skills import SkillType, Skills


class TestSkills():

    def test_to_json(self):
        skills = Skills()
        skills.set(SkillType.HIDE, 5)
        skills.set(SkillType.SEARCH, 3)
        skills.set(SkillType.PICK_LOCK, 1)

        expected_json = {
            SkillType.HIDE.value: 5,
            SkillType.SEARCH.value: 3,
            SkillType.PICK_LOCK.value: 1
        }

        assert skills.to_json() == expected_json

    def test_from_json(self):
        json_data = {
            SkillType.HIDE.value: 5,
            SkillType.SEARCH.value: 3,
            SkillType.PICK_LOCK.value: 1
        }

        expected_skills = Skills()
        expected_skills.set(SkillType.HIDE, 5)
        expected_skills.set(SkillType.SEARCH, 3)
        expected_skills.set(SkillType.PICK_LOCK, 1)

        assert Skills.from_json(json_data) == expected_skills