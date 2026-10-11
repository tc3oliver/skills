from solution import effective_flag
assert effective_flag({'enabled':False}) is False
assert effective_flag({}) is True
assert effective_flag({'enabled':True},False) is True
assert effective_flag({},False) is False
