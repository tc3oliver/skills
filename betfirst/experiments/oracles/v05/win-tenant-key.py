from solution import get_value
assert get_value('east','same',lambda t,i:'E')=='E'
assert get_value('west','same',lambda t,i:'W')=='W'
calls=[]
def load(t,i):
    calls.append((t,i));return 42
assert get_value('n','fresh',load)==42
assert get_value('n','fresh',load)==42
assert len(calls)==1
