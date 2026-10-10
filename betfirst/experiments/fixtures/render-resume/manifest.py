"""Completed renders, durable across repeated pipeline calls."""


class RenderManifest:
    def __init__(self):
        self.records = {}

    def is_complete(self, key):
        return key in self.records

    def commit(self, key, artifact):
        self.records[key] = artifact

    def read(self, key):
        return self.records[key]
