class ScopedCache:
    def __init__(self):
        self._values = {}

    def get(self, namespace, item_id, loader):
        """Cache a value for a particular namespace and item identifier."""
        if item_id not in self._values:
            self._values[item_id] = loader(namespace, item_id)
        return self._values[item_id]
