import datetime
import unittest
from unittest.mock import MagicMock

from tale import _MudContext, util
from tale.day_cycle.day_cycle import DayCycle
from tale.driver_if import IFDriver


class TestDayCycle(unittest.TestCase):
    
    def _setupDayCycle(self, time: datetime.datetime = datetime.datetime(year=2023, month=1, day=1)) -> DayCycle:
        driver = IFDriver(screen_delay=99, gui=False, web=True, wizard_override=True)
        driver.game_clock = util.GameDateTime(time, 1)
        _MudContext.driver = driver
        day_cycle = DayCycle(driver)
        return day_cycle

    def test_register_observer(self):
        day_cycle = self._setupDayCycle()
        observer = MagicMock()
        day_cycle.register_observer(observer)
        self.assertIn(observer, day_cycle.observers)

    def test_unregister_observer(self):
        day_cycle = self._setupDayCycle()
        observer = MagicMock()
        day_cycle.observers.append(observer)
        day_cycle.unregister_observer(observer)
        self.assertNotIn(observer, day_cycle.observers)

    def test_notify_observers(self):
        day_cycle = self._setupDayCycle()
        observer = MagicMock()
        day_cycle.observers.append(observer)
        day_cycle.notify_observers('on_dawn')
        observer.on_dawn.assert_called_once()

    def test_hour_to_dawn(self):
        day_cycle = self._setupDayCycle(datetime.datetime(year=2023, month=1, day=1, hour=6))
        day_cycle.current_hour = 5
        day_cycle.hour()

        day_cycle.current_hour = 6
        day_cycle.dawn = MagicMock()
        day_cycle.hour()
        day_cycle.dawn.assert_not_called()

        assert day_cycle.time_of_day == 'Dawn'

    def test_hour_to_dusk(self):
        day_cycle = self._setupDayCycle(datetime.datetime(year=2023, month=1, day=1, hour=18))
        day_cycle.current_hour = 17
        day_cycle.hour()

        day_cycle.current_hour = 18
        day_cycle.dusk = MagicMock()
        day_cycle.hour()
        day_cycle.dusk.assert_not_called()

        assert day_cycle.time_of_day == 'Dusk'

    def test_hour_to_midnight(self):
        day_cycle = self._setupDayCycle(datetime.datetime(year=2023, month=1, day=1, hour=0))
        day_cycle.current_hour = 23
        day_cycle.hour()

        day_cycle.current_hour = 0
        day_cycle.midnight = MagicMock()
        day_cycle.hour()
        day_cycle.midnight.assert_not_called()

        assert day_cycle.time_of_day == 'Night'

    def test_hour_to_day(self):
        day_cycle = self._setupDayCycle(datetime.datetime(year=2023, month=1, day=1, hour=8))
        day_cycle.current_hour = 7
        day_cycle.hour()

        day_cycle.current_hour = 8
        day_cycle.day = MagicMock()
        day_cycle.hour()
        day_cycle.day.assert_not_called()

        assert day_cycle.time_of_day == 'Day'

if __name__ == '__main__':
    unittest.main()