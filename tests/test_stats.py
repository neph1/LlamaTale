

from tale.base import Stats


class TestStats:

    def test_replenish_hp(self):
        stats = Stats()
        stats.max_hp = 100
        stats.hp = 0

        stats.replenish_hp(10)

        assert stats.hp == 10

        stats.replenish_hp()

        assert stats.hp == 100

    def test_replenish_combat_points(self):
        stats = Stats()
        stats.max_action_points = 100
        stats.action_points = 0

        stats.replenish_combat_points(10)

        assert stats.action_points == 10

        stats.replenish_combat_points()

        assert stats.action_points == 100