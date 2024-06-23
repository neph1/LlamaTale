import unittest
from unittest.mock import MagicMock

from tale.day_cycle.day_cycle import DayCycle


class TestDayCycle(unittest.TestCase):
    def setUp(self):
        self.game_date_time = MagicMock()
        self.day_cycle = DayCycle(self.game_date_time)

    def test_register_observer(self):
        observer = MagicMock()
        self.day_cycle.register_observer(observer)
        self.assertIn(observer, self.day_cycle.observers)

    def test_unregister_observer(self):
        observer = MagicMock()
        self.day_cycle.observers.append(observer)
        self.day_cycle.unregister_observer(observer)
        self.assertNotIn(observer, self.day_cycle.observers)

    def test_notify_observers(self):
        observer = MagicMock()
        self.day_cycle.observers.append(observer)
        self.day_cycle.notify_observers('on_dawn')
        observer.on_dawn.assert_called_once()

    def test_set_hour_interval(self):
        hour_decorator = self.day_cycle.set_hour_interval(3600)
        self.assertIsNotNone(hour_decorator)

    def test_hour_to_dawn(self):
        self.day_cycle.current_hour = 5
        self.day_cycle.dawn = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.dawn.assert_called_once()

        self.day_cycle.current_hour = 6
        self.day_cycle.dawn = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.dawn.assert_not_called()

    def test_hour_to_dusk(self):
        self.day_cycle.current_hour = 17
        self.day_cycle.dusk = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.dusk.assert_called_once()

        self.day_cycle.current_hour = 18
        self.day_cycle.dusk = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.dusk.assert_not_called()

    def test_hour_to_midnight(self):
        self.day_cycle.current_hour = 23
        self.day_cycle.midnight = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.midnight.assert_called_once()

        self.day_cycle.current_hour = 24
        self.day_cycle.midnight = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.midnight.assert_not_called()

    def test_hour_to_day(self):
        self.day_cycle.current_hour = 7
        self.day_cycle.day = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.day.assert_called_once()

        self.day_cycle.current_hour = 8
        self.day_cycle.day = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.day.assert_not_called()

if __name__ == '__main__':
    unittest.main()