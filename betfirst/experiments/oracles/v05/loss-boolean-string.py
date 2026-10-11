from solution import to_bool
assert to_bool('false') is False
assert to_bool('TRUE') is True
assert to_bool('FALSE') is False
try:
 to_bool('maybe')
except ValueError:
 pass
else:
 raise AssertionError('invalid string should fail')
