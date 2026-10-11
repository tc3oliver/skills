"""An expiry cache. False is a valid cached value."""


class ExpiringCache:
    def __init__(self, clock, ttl=60):
        self.clock = clock
        self.ttl = ttl
        self.entries = {}

    def get(self, key):
        item = self.entries.get(key)
        if item is None:
            return None
        value, expires = item
        if self.clock() >= expires:
            del self.entries[key]
            return None
        return (value, expires)

    def put(self, key, value):
        self.entries[key] = (value, self.clock() + self.ttl)
