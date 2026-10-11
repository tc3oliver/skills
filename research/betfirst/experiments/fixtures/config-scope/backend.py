"""Configuration source: values can differ between tenants."""


class FlagBackend:
    def __init__(self, values):
        self.values = dict(values)
        self.reads = []

    def read(self, tenant, flag):
        self.reads.append((tenant, flag))
        return self.values[(tenant, flag)]
