# -*- coding: utf-8 -*-
"""시뮬레이터 모델 단위 테스트: python -m unittest discover -s tests"""
import unittest
from datetime import datetime, timedelta, timezone

from todak_sim.model import Greenhouse, is_active

KST = timezone(timedelta(hours=9))


class ModelTest(unittest.TestCase):
    def run_hours(self, g, start, hours):
        t = start
        v = None
        for _ in range(hours * 60):
            v = g.step(t)
            t += timedelta(minutes=1)
        return v

    def test_all_eleven_channels(self):
        v = Greenhouse().step(datetime(2026, 10, 26, 12, 0, tzinfo=KST))
        self.assertEqual(len(v), 11)

    def test_heater_raises_night_temperature(self):
        night = datetime(2026, 1, 15, 2, 0, tzinfo=KST)
        cold = self.run_hours(Greenhouse(), night, 3)["S-T01"]
        g = Greenhouse()
        g.devices["D-HEAT01"] = "ON"
        warm = self.run_hours(g, night, 3)["S-T01"]
        self.assertGreater(warm, cold + 5)

    def test_vents_cool_hot_house(self):
        noon = datetime(2026, 7, 15, 11, 0, tzinfo=KST)
        closed = self.run_hours(Greenhouse(), noon, 2)["S-T02"]
        g = Greenhouse()
        g.devices["D-VENT01"] = g.devices["D-VENT02"] = "OPEN"
        g.devices["D-FAN01"] = g.devices["D-FAN02"] = "ON"
        opened = self.run_hours(g, noon, 2)["S-T02"]
        self.assertLess(opened, closed - 3)

    def test_irrigation_raises_substrate_moisture(self):
        t = datetime(2026, 10, 26, 12, 0, tzinfo=KST)
        g = Greenhouse()
        before = g.sm["Z1"]
        g.devices["D-VALVE01"] = "ON"
        self.run_hours(g, t, 1)
        self.assertGreater(g.sm["Z1"], before)

    def test_active_state_by_type(self):
        self.assertTrue(is_active("D-VENT01", "OPEN"))
        self.assertTrue(is_active("D-SHADE01", "CLOSE"))
        self.assertTrue(is_active("D-FAN01", "ON"))
        self.assertFalse(is_active("D-HEAT01", "OFF"))


if __name__ == "__main__":
    unittest.main()
