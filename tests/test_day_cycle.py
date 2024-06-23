import datetime
import unittest
from unittest.mock import MagicMock

from tale import _MudContext, util
from tale.day_cycle.day_cycle import DayCycle
from tale.driver_if import IFDriver


class TestDayCycle(unittest.TestCase):
    def setUp(self):
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1), 1)
        _MudContext.driver = driver
        self.day_cycle = DayCycle(driver.game_clock)

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

    def test_hour_to_dawn(self):
        clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1, hour=6))
        self.day_cycle = DayCycle(clock)
        self.day_cycle.current_hour = 5
        self.day_cycle.hour()

        self.day_cycle.current_hour = 6
        self.day_cycle.dawn = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.dawn.assert_not_called()

        assert self.day_cycle.time_of_day == 'Dawn'

    def test_hour_to_dusk(self):
        clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1, hour=18))
        self.day_cycle = DayCycle(clock)
        self.day_cycle.current_hour = 17
        self.day_cycle.hour()

        self.day_cycle.current_hour = 18
        self.day_cycle.dusk = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.dusk.assert_not_called()

        assert self.day_cycle.time_of_day == 'Dusk'

    def test_hour_to_midnight(self):
        clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1, hour=0))
        self.day_cycle = DayCycle(clock)
        self.day_cycle.current_hour = 23
        self.day_cycle.hour()

        self.day_cycle.current_hour = 0
        self.day_cycle.midnight = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.midnight.assert_not_called()

        assert self.day_cycle.time_of_day == 'Night'

    def test_hour_to_day(self):
        clock = util.GameDateTime(datetime.datetime(year=2023, month=1, day=1, hour=8))
        self.day_cycle = DayCycle(clock)
        self.day_cycle.current_hour = 7
        self.day_cycle.hour()

        self.day_cycle.current_hour = 8
        self.day_cycle.day = MagicMock()
        self.day_cycle.hour()
        self.day_cycle.day.assert_not_called()

        assert self.day_cycle.time_of_day == 'Day'

if __name__ == '__main__':
    unittest.main()