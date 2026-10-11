"""Independent black-box acceptance; not copied into an agent workspace."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path.cwd()))

from backend import FlagBackend
from cache import ExpiringCache
from service import FeatureFlagService


class Oracle(unittest.TestCase):
    def test_cross_tenant_same_flag_must_not_leak(self):
        now = [100]
        backend = FlagBackend({
            ("alpha", "vision"): True, ("bravo", "vision"): False,
            ("alpha", "voice"): False, ("bravo", "voice"): True,
        })
        service = FeatureFlagService(backend, ExpiringCache(lambda: now[0], ttl=10))
        self.assertTrue(service.enabled("alpha", "vision"))
        self.assertFalse(service.enabled("bravo", "vision"))
        self.assertFalse(service.enabled("alpha", "voice"))
        self.assertTrue(service.enabled("bravo", "voice"))
        for tenant, flag in backend.values:
            self.assertEqual(service.enabled(tenant, flag), backend.values[(tenant, flag)])
        self.assertEqual(len(backend.reads), 4, "Cache must not be disabled to pass")

    def test_expiry_reloads_per_tenant(self):
        t = [0]
        backend = FlagBackend({("A", "x"): False, ("B", "x"): True})
        service = FeatureFlagService(backend, ExpiringCache(lambda: t[0], ttl=30))
        self.assertFalse(service.enabled("A", "x"))
        self.assertTrue(service.enabled("B", "x"))
        backend.values[("A", "x")] = True
        backend.values[("B", "x")] = False
        t[0] = 29
        self.assertFalse(service.enabled("A", "x"))
        self.assertTrue(service.enabled("B", "x"))
        t[0] = 30
        self.assertTrue(service.enabled("A", "x"))
        self.assertFalse(service.enabled("B", "x"))
        self.assertEqual(len(backend.reads), 4)


if __name__ == "__main__":
    unittest.main()
