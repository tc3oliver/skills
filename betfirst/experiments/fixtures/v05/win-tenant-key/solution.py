_cache={}
def get_value(tenant, item, loader):
    if item not in _cache:
        _cache[item]=loader(tenant,item)
    return _cache[item]
