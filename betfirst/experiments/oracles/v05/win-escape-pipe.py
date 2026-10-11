from solution import split_fields
assert split_fields(r'a\|b|c')==['a|b','c']
assert split_fields(r'a\\|b')==['a\\','b']
assert split_fields('a||')==['a','','']
