import unittest

from backend import FlagBackend
from cache import ExpiringCache
from service import FeatureFlagService


class FlagTests(unittest.TestCase):
    def test_cache_hit_and_expiry(self):
        now = [10]
        backend = FlagBackend({("alpha", "beta"): False})
        service = FeatureFlagService(backend, ExpiringCache(lambda: now[0], ttl=20))
        self.assertFalse(service.enabled("alpha", "beta"))
        backend.values[("alpha", "beta")] = True
        self.assertFalse(service.enabled("alpha", "beta"))
        self.assertEqual(len(backend.reads), 1)
        now[0] = 30
        self.assertTrue(service.enabled("alpha", "beta"))
        self.assertEqual(len(backend.reads), 2)


if __name__ == "__main__":
    unittest.main()
