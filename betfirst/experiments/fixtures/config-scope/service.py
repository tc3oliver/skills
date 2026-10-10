"""Serve a feature flag for a tenant with bounded caching."""


class FeatureFlagService:
    def __init__(self, backend, cache):
        self.backend = backend
        self.cache = cache

    def enabled(self, tenant, flag):
        cache_key = flag
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached[0]
        value = self.backend.read(tenant, flag)
        self.cache.put(cache_key, value)
        return value
